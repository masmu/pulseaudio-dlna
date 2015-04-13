#!/usr/bin/python

# This file is part of pulseaudio-dlna.

# pulseaudio-dlna is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# pulseaudio-dlna is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with pulseaudio-dlna.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals

import sys
import re
import subprocess
import threading
import setproctitle
import logging
import time
import socket
import select
import atexit
import json
import BaseHTTPServer
import SocketServer

import pulseaudio_dlna.encoders
import pulseaudio_dlna.recorders
import pulseaudio_dlna.common

from pulseaudio_dlna.plugins.upnp.renderer import (
    UpnpContentFeatures, UpnpContentFlags)


class RemoteDevice(object):
    def __init__(self, bridge, sock):
        self.bridge = bridge
        try:
            self.ip, self.port = sock.getsockname()
        except:
            logging.info('Could not get socket IP and Port. Setting to '
                         'unknown.')
            self.ip = 'unknown'
            self.port = 'unknown'


class ProcessStream(object):
    def __init__(self, path, recorder, encoder, server):
        self.path = path
        self.recorder = recorder
        self.encoder = encoder
        self.recorder_process = None
        self.encoder_process = None
        self.server = server

        self.sockets = {}
        self.chunk_size = 1024 * 4
        self.lock = threading.Lock()
        self.client_count = 0

        atexit.register(self.shutdown)

        class UpdateThread(threading.Thread):
            def __init__(self, stream):
                threading.Thread.__init__(self)
                self.stream = stream
                self.is_running = False
                self.lock = threading.Lock()
                self.lock.acquire()

            def run(self):
                while True:
                    if self.is_running is False:
                        self.lock.acquire()
                    else:
                        self.stream.communicate()

            def pause(self):
                self.is_running = False

            def resume(self):
                if self.is_running is False:
                    self.is_running = True
                    self.lock.release()

        self.update_thread = UpdateThread(self)
        self.update_thread.daemon = True
        self.update_thread.start()

    @property
    def mime_type(self):
        return self.encoder.mime_type

    def register(self, bridge, sock, lock_override=False):
        if sock not in self.sockets:
            try:
                if not lock_override:
                    self.lock.acquire()
                device = RemoteDevice(bridge, sock)
                logging.info(
                    'Client {client} registered to stream {path}.'.format(
                        client=device.ip,
                        path=self.path))
                self.sockets[sock] = device
                self.client_count += 1
                self.update_thread.resume()
            finally:
                if not lock_override:
                    self.lock.release()
        else:
            logging.info('The same client id tries to register a stream, this '
                         'should never happen...')
            sys.exit(2)

    def unregister(self, sock, lock_override=False, method=0):
        if sock in self.sockets:
            try:
                if not lock_override:
                    self.lock.acquire()
                logging.info(
                    'Client {client} unregistered stream {path} '
                    'using method {method}.'.format(
                        client=self.sockets[sock].ip,
                        method=method,
                        path=self.path))
                bridge = self.sockets[sock].bridge
                del self.sockets[sock]
                sock.close()
                self.client_count -= 1
                if len(self.sockets) == 0:
                    self.server.message_queue.put(
                        {'type': 'on_bridge_disconnected',
                         'stopped_bridge': bridge})
                    logging.info('Stream closed. '
                                 'Cleaning up remaining processes ...')
                    self.update_thread.pause()
                    self.cleanup()
            finally:
                if not lock_override:
                    self.lock.release()
        else:
            logging.info('A client id tries to unregister a stream which is '
                         'not registered, this should never happen...')
            sys.exit(2)

    def communicate(self):
        try:
            self.lock.acquire()

            if not self.do_processes_exist():
                self.create_processes()
                logging.info(
                    'Processes of {path} initialized ...'.format(
                        path=self.path))
            if not self.do_processes_respond():
                self.cleanup()
                self.create_processes()
                logging.info(
                    'Processes of {path} reinitialized ...'.format(
                        path=self.path))

            data = self.encoder_process.stdout.read(self.chunk_size)
            socks = self.sockets.keys()
            try:
                r, w, e = select.select(socks, socks, [], 0)
            except socket.error:
                for sock in socks:
                    try:
                        r, w, e = select.select([sock], [], [], 0)
                    except socket.error:
                        self.unregister(sock, lock_override=True, method=1)
                return

            for sock in w:
                try:
                    self._send_data(sock, data)
                except socket.error:
                    self.unregister(sock, lock_override=True, method=2)

            for sock in r:
                if sock in self.sockets:
                    try:
                        data = sock.recv(1024)
                        if len(data) == 0:
                            self.unregister(sock, lock_override=True, method=3)
                    except socket.error:
                        self.unregister(sock, lock_override=True, method=4)

        finally:
            self.lock.release()

    def _send_data(self, sock, data):
        bytes_total = len(data)
        bytes_sent = 0
        while bytes_sent < bytes_total:
            bytes_sent += sock.send(data[bytes_sent:])

    def do_processes_exist(self):
        return (self.encoder_process is not None and
                self.recorder_process is not None)

    def do_processes_respond(self):
        return (self.recorder_process.poll() is None and
                self.encoder_process.poll() is None)

    def cleanup(self):
        self._kill_process(self.encoder_process)
        self._kill_process(self.recorder_process)

    def _kill_process(self, process):
        try:
            process.kill()
        except:
            pass

    def create_processes(self):
        logging.debug('Starting processes "{recorder} | {encoder}"'.format(
            recorder=self.recorder.command,
            encoder=self.encoder.command))
        self.recorder_process = subprocess.Popen(
            self.recorder.command.split(' '),
            stdout=subprocess.PIPE)
        self.encoder_process = subprocess.Popen(
            self.encoder.command.split(' '),
            stdin=self.recorder_process.stdout,
            stdout=subprocess.PIPE)
        self.recorder_process.stdout.close()

    def shutdown(self):
        logging.info('Streaming server is shutting down.')
        for sock in self.sockets.keys():
            sock.close()


class StreamManager(object):
    def __init__(self, server):
        self.streams = {}
        self.server = server

    def get_stream(self, path, bridge, encoder):
        if path not in self.streams:
            recorder = pulseaudio_dlna.recorders.PulseaudioRecorder(
                bridge.sink.monitor)
            stream = ProcessStream(
                path,
                recorder,
                encoder,
                self.server,
            )
            self.streams[path] = stream
            return stream
        else:
            return self.streams[path]


class StreamRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def __init__(self, *args):
        try:
            BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *args)
        except IOError:
            pass

    def do_HEAD(self):
        logging.debug('Got the following HEAD request:\n{header}'.format(
            header=json.dumps(self.headers.items(), indent=2)))
        self.handle_headers()

    def do_GET(self):
        logging.debug('Got the following GET request:\n{header}'.format(
            header=json.dumps(self.headers.items(), indent=2)))
        bridge, encoder = self.handle_headers()
        if bridge and encoder:
            stream = self.server.stream_manager.get_stream(
                self.path, bridge, encoder)
            stream.register(bridge, self.request)
            self.keep_connection_alive()

    def keep_connection_alive(self):
        self.close_connection = 0
        self.wfile.flush()

        while True:
            try:
                r, w, e = select.select([self.request], [], [], 0)
            except socket.error:
                logging.debug('Socket died, releasing request thread.')
                break
            time.sleep(1)

    def handle_headers(self):
        bridge, encoder = self.chop_request_path(self.path)
        if encoder and bridge:
            self.send_response(200)
            headers = {
                'Content-Type': encoder.mime_type,
                'Connection': 'close',
            }

            if isinstance(
                bridge.device,
                    pulseaudio_dlna.plugins.upnp.renderer.UpnpMediaRenderer):
                content_features = UpnpContentFeatures(
                    flags=[
                        UpnpContentFlags.STREAMING_TRANSFER_MODE_SUPPORTED,
                        UpnpContentFlags.BACKGROUND_TRANSFER_MODE_SUPPORTED,
                        UpnpContentFlags.CONNECTION_STALLING_SUPPORTED,
                        UpnpContentFlags.DLNA_VERSION_15_SUPPORTED
                    ])
                headers['contentFeatures.dlna.org'] = str(content_features)
                headers['Ext'] = ''
                headers['transferMode.dlna.org'] = 'Streaming'

            logging.debug('Sending header:\n{header}'.format(
                header=json.dumps(headers, indent=2)))
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            return bridge, encoder
        else:
            logging.info('Error 404: File not found "{}"'.format(self.path))
            self.send_error(404, 'File not found: %s' % self.path)
            return None, None

    def chop_request_path(self, path):
        logging.info('Requested streaming URL was: {path}'.format(
            path=path))
        try:
            short_name, suffix = re.findall(r"/(.*?)\.(.*)", path)[0]

            choosen_encoder = None
            for encoder in pulseaudio_dlna.common.supported_encoders:
                if encoder.suffix == suffix:
                    choosen_encoder = encoder
                    break

            choosen_bridge = None
            for bridge in self.server.bridges:
                if short_name == bridge.device.short_name:
                    choosen_bridge = bridge
                    break

            if choosen_bridge is not None and choosen_encoder is not None:
                return bridge, encoder

        except (TypeError, ValueError, IndexError):
            pass
        return None, None


class StreamServer(SocketServer.TCPServer):

    def __init__(self, ip, port, bridges, message_queue, *args):
        setproctitle.setproctitle('stream_server')
        SocketServer.TCPServer.allow_reuse_address = True
        SocketServer.TCPServer.__init__(
            self, ('', port), StreamRequestHandler, *args)

        self.ip = ip
        self.port = port
        self.bridges = bridges
        self.message_queue = message_queue
        self.stream_manager = StreamManager(self)

    def get_server_url(self):
        return 'http://{ip}:{port}'.format(
            ip=self.ip,
            port=self.port,
        )

    def run(self):
        setproctitle.setproctitle('dlna_server')
        SocketServer.TCPServer.serve_forever(self)


class ThreadedStreamServer(SocketServer.ThreadingMixIn, StreamServer):
    pass
