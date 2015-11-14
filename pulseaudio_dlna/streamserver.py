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

import re
import subprocess
import threading
import setproctitle
import logging
import time
import socket
import select
import sys
import gobject
import functools
import atexit
import base64
import urllib
import json
import os
import signal
import pkg_resources
import BaseHTTPServer
import SocketServer

import pulseaudio_dlna.encoders
import pulseaudio_dlna.codecs
import pulseaudio_dlna.recorders
import pulseaudio_dlna.rules
import pulseaudio_dlna.images

from pulseaudio_dlna.plugins.upnp.renderer import (
    UpnpContentFeatures, UpnpContentFlags)

logger = logging.getLogger('pulseaudio_dlna.streamserver')

PROTOCOL_VERSION_V10 = 'HTTP/1.0'
PROTOCOL_VERSION_V11 = 'HTTP/1.1'


@functools.total_ordering
class RemoteDevice(object):
    def __init__(self, bridge, sock):
        self.bridge = bridge
        self.sock = sock
        try:
            self.ip, self.port = sock.getpeername()
        except:
            logger.info('Could not get socket IP and Port. Setting to '
                        'unknown.')
            self.ip = 'unknown'
            self.port = 'unknown'

    def __eq__(self, other):
        if isinstance(other, RemoteDevice):
            return self.ip == other.ip
        raise NotImplementedError

    def __gt__(self, other):
        if isinstance(other, RemoteDevice):
            return self.ip > other.ip
        raise NotImplementedError

    def __str__(self):
        return '<{} socket="{}" ip="{}" port="{}">'.format(
            self.__class__.__name__,
            str(self.sock),
            self.ip,
            self.port,
        )


@functools.total_ordering
class ProcessStream(object):
    def __init__(self, path, recorder, encoder, manager):
        self.id = hex(id(self))
        self.path = path
        self.recorder = recorder
        self.encoder = encoder
        self.recorder_process = None
        self.encoder_process = None
        self.manager = manager

        self.sockets = {}
        self.timeouts = {}
        self.chunk_size = 1024 * 4
        self.lock = threading.Lock()
        self.client_count = 0
        self.reinitialize_count = 0

        atexit.register(self.shutdown)

        gobject.timeout_add(
            10000, self._on_regenerate_reinitialize_count)

        class UpdateThread(threading.Thread):
            def __init__(self, stream):
                threading.Thread.__init__(self)
                self.stream = stream
                self.is_running = False
                self.do_stop = False
                self.lock = threading.Lock()
                self.lock.acquire()

            def run(self):
                while True:
                    if self.do_stop:
                        break
                    elif self.is_running is False:
                        self.lock.acquire()
                    else:
                        self.stream.communicate()
                logger.info('Thread stopped for "{}".'.format(
                    self.stream.path))

            def stop(self):
                self.do_stop = True
                if self.is_running is False:
                    self.is_running = True
                    self.lock.release()

            def pause(self):
                self.is_running = False

            def resume(self):
                if self.do_stop:
                    logger.error('Trying to resume a stopped thread!')
                if self.is_running is False:
                    self.is_running = True
                    self.lock.release()

            @property
            def state(self):
                if self.do_stop:
                    return 'stopped'
                if self.is_running:
                    return 'running'
                else:
                    return 'paused'

        self.update_thread = UpdateThread(self)
        self.update_thread.daemon = True
        self.update_thread.start()

    def register(self, bridge, sock, lock_override=False):
        try:
            if not lock_override:
                self.lock.acquire()
            device = RemoteDevice(bridge, sock)
            logger.info(
                'Client {client} registered to stream {path}.'.format(
                    client=device.ip,
                    path=self.path))
            self.sockets[sock] = device
            self.client_count += 1
            self.update_thread.resume()
        finally:
            if not lock_override:
                self.lock.release()

    def unregister(self, sock, lock_override=False, method=0):
        try:
            if not lock_override:
                self.lock.acquire()
            try:
                device = self.sockets[sock]
                del self.sockets[sock]
                sock.close()
            except KeyError:
                logger.info('A client id tries to unregister a stream which is '
                            'not registered, this should never happen...')
                return

            logger.info(
                'Client {client} unregistered stream {path} '
                'using method {method}.'.format(
                    client=device.ip,
                    method=method,
                    path=self.path))

            if device.ip in self.timeouts:
                gobject.source_remove(self.timeouts[device.ip])
            self.timeouts[device.ip] = gobject.timeout_add(
                2000, self._on_delayed_disconnect, device)

            self.client_count -= 1
        finally:
            if not lock_override:
                self.lock.release()

    def _on_regenerate_reinitialize_count(self):
        if self.reinitialize_count > 0:
            self.reinitialize_count -= 1
        return True

    def _on_delayed_disconnect(self, device):
        self.timeouts.pop(device.ip)

        if len(self.sockets) == 0:
            logger.info('Stream closed. '
                        'Cleaning up remaining processes ...')
            self.update_thread.pause()
            self.terminate_processes()

        self.manager._on_device_disconnect(device, self)
        return False

    def communicate(self):
        try:
            self.lock.acquire()

            if not self.do_processes_exist():
                self.create_processes()
                logger.info(
                    'Processes of {path} initialized ...'.format(
                        path=self.path))
            if not self.do_processes_respond():
                self.terminate_processes()
                self.create_processes()
                logger.info(
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
                        logger.info(
                            'Read data from socket "{}"'.format(data))
                        if len(data) == 0:
                            self.unregister(sock, lock_override=True, method=3)
                    except socket.error:
                        logger.error(
                            'Error while reading from socket ...')

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

    def terminate_processes(self):

        def _kill_process(process):
            pid = process.pid
            try:
                os.kill(pid, signal.SIGTERM)
                _pid, return_code = os.waitpid(pid, 0)
            except:
                try:
                    os.kill(pid, signal.SIGKILL)
                except:
                    pass

        _kill_process(self.encoder_process)
        _kill_process(self.recorder_process)

    def create_processes(self):
        if self.reinitialize_count < 3:
            self.reinitialize_count += 1
            logger.debug('Starting processes "{recorder} | {encoder}"'.format(
                recorder=' '.join(self.recorder.command),
                encoder=' '.join(self.encoder.command)))
            self.recorder_process = subprocess.Popen(
                self.recorder.command,
                stdout=subprocess.PIPE)
            self.encoder_process = subprocess.Popen(
                self.encoder.command,
                stdin=self.recorder_process.stdout,
                stdout=subprocess.PIPE)
            self.recorder_process.stdout.close()
        else:
            self.update_thread.pause()
            logger.error('There were more than {} attempts to reinitialize '
                         'the record process. Aborting.'.format(
                             self.reinitialize_count))

    def shutdown(self, *args):
        self.update_thread.stop()
        for sock in self.sockets.keys():
            sock.close()
        logger.info('Thread exited for "{}".'.format(self.path))

    def __eq__(self, other):
        if isinstance(other, ProcessStream):
            return self.path == other.path
        raise NotImplementedError

    def __gt__(self, other):
        if isinstance(other, ProcessStream):
            return self.path > other.path
        raise NotImplementedError

    def __str__(self):
        return '<{} id="{}" path="{}" state="{}">\n{}'.format(
            self.__class__.__name__,
            self.id,
            self.path,
            self.update_thread.state,
            '\n'.join(['      ' + str(device) for device in self.sockets.values()]),
        )


class StreamManager(object):
    def __init__(self, server):
        self.single_streams = []
        self.shared_streams = {}
        self.server = server

    def _on_device_disconnect(self, remote_device, stream):

        def _send_bridge_disconnected(bridge):
            logger.info('Device "{}" disconnected.'.format(bridge.device.name))
            self.server.message_queue.put({
                'type': 'on_bridge_disconnected',
                'stopped_bridge': bridge,
            })

        if isinstance(
                remote_device.bridge.device.codec,
                pulseaudio_dlna.codecs.WavCodec):
            self.single_streams = [
                s for s in self.single_streams if stream.id != s.id]

            if stream not in self.single_streams:
                _send_bridge_disconnected(remote_device.bridge)
            stream.shutdown()
        else:
            if remote_device not in stream.sockets.values():
                _send_bridge_disconnected(remote_device.bridge)

    def _create_stream(self, path, bridge):
        return ProcessStream(
            path,
            bridge.device.codec.get_recorder(bridge.sink.monitor),
            bridge.device.codec.encoder,
            self,
        )

    def get_stream(self, path, bridge):
        if isinstance(bridge.device.codec, pulseaudio_dlna.codecs.WavCodec):
            # always create a seperate process stream for wav codecs
            # since the client devices require the wav header which is
            # just send at the beginning of each encoding process
            stream = self._create_stream(path, bridge)
            self.single_streams.append(stream)
            return stream
        else:
            # all other codecs can share a process stream depending
            # on their path
            if path not in self.shared_streams:
                stream = self._create_stream(path, bridge)
                self.shared_streams[path] = stream
                return stream
            else:
                return self.shared_streams[path]

    def __str__(self):
        return '<{}>\n  single:\n{}\n  shared:\n{}\n'.format(
            self.__class__.__name__,
            '\n'.join(['    ' + str(stream) for stream in self.single_streams]),
            '\n'.join(['    ' + str(stream) for stream in self.shared_streams.values()]),
        )


class StreamRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def __init__(self, *args):
        try:
            BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *args)
        except IOError:
            pass

    def do_HEAD(self):
        logger.debug('Got the following HEAD request:\n{header}'.format(
            header=json.dumps(self.headers.items(), indent=2)))
        item = self.get_requested_item()
        self.handle_headers(item)

    def do_GET(self):
        logger.debug('Got the following GET request:\n{header}'.format(
            header=json.dumps(self.headers.items(), indent=2)))
        item = self.get_requested_item()
        self.handle_headers(item)
        if isinstance(item, pulseaudio_dlna.images.BaseImage):
            self.wfile.write(item.data)
        elif isinstance(item, pulseaudio_dlna.pulseaudio.PulseBridge):
            stream = self.server.stream_manager.get_stream(self.path, item)
            stream.register(item, self.request)
            self.keep_connection_alive()

    def keep_connection_alive(self):
        self.close_connection = 0
        self.wfile.flush()

        while True:
            try:
                r, w, e = select.select([self.request], [], [], 0)
            except socket.error:
                logger.debug('Socket died, releasing request thread.')
                break
            time.sleep(1)

    def handle_headers(self, item):
        response_code = 200
        headers = {}

        if not item:
            logger.info('Error 404: File not found "{}"'.format(self.path))
            self.send_error(404, 'File not found: %s' % self.path)
            return
        elif isinstance(item, pulseaudio_dlna.images.BaseImage):
            image = item
            headers['Content-Type'] = image.content_type
        elif isinstance(item, pulseaudio_dlna.pulseaudio.PulseBridge):
            bridge = item
            headers['Content-Type'] = bridge.device.codec.specific_mime_type

            if self.server.fake_http_content_length or \
               pulseaudio_dlna.rules.FAKE_HTTP_CONTENT_LENGTH in bridge.device.codec.rules:
                gb_in_bytes = pow(1024, 3)
                headers['Content-Length'] = gb_in_bytes * 100
            else:
                if self.request_version == PROTOCOL_VERSION_V10:
                    pass
                elif self.request_version == PROTOCOL_VERSION_V11:
                    headers['Connection'] = 'close'

            if self.headers.get('range'):
                match = re.search(
                    'bytes=(\d+)-(\d+)?', self.headers['range'], re.IGNORECASE)
                if match:
                    start_range = int(match.group(1))
                    if start_range != 0:
                        response_code = 206

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

        logger.debug('Sending header ({response_code}):\n{header}'.format(
            response_code=response_code,
            header=json.dumps(headers, indent=2),
        ))
        self.send_response(response_code)
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()

    def get_requested_item(self):
        settings = self._decode_settings(self.path)
        if settings.get('type', None) == 'bridge':
            for bridge in self.server.bridges:
                if settings.get('udn') == bridge.device.udn:
                    return bridge
        elif settings.get('type', None) == 'image':
            image_name = settings.get('name', None)
            if image_name:
                image_path = pkg_resources.resource_filename(
                    'pulseaudio_dlna.streamserver', os.path.join(
                        'images', image_name))
                try:
                    _type = pulseaudio_dlna.images.get_type_by_filepath(
                        image_path)
                    return _type(path=image_path, cached=True)
                except (pulseaudio_dlna.images.UnknownImageExtension,
                        pulseaudio_dlna.images.ImageNotAccessible,
                        pulseaudio_dlna.images.MissingDependencies,
                        pulseaudio_dlna.images.IconNotFound) as e:
                    logger.error(e)
        elif settings.get('type', None) == 'sys-icon':
            icon_name = settings.get('name', None)
            if icon_name:
                try:
                    return pulseaudio_dlna.images.get_icon_by_name(
                        icon_name, size=512)
                except (pulseaudio_dlna.images.UnknownImageExtension,
                        pulseaudio_dlna.images.ImageNotAccessible,
                        pulseaudio_dlna.images.MissingDependencies,
                        pulseaudio_dlna.images.IconNotFound) as e:
                    logger.error(e)
        return None

    def _decode_settings(self, path):
        try:
            data_quoted = re.findall(r'/(.*?)/', path)[0]
            data_string = base64.b64decode(urllib.unquote(data_quoted))
            settings = {
                k: v for k, v in re.findall('(.*?)="(.*?)",?', data_string)
            }
            logger.info(
                'URL settings: {path} ({data_string})'.format(
                    path=path,
                    data_string=data_string))
            return settings
        except (TypeError, ValueError, IndexError):
            pass
        return {}

    def log_message(self, format, *args):
        args = [unicode(arg) for arg in args]
        logger.info('Got request from {host} - {args}' .format(
            host=self.address_string(),
            time=self.log_date_time_string(),
            args=','.join(args)))


class StreamServer(SocketServer.TCPServer):

    def __init__(
            self, ip, port, bridges, message_queue,
            fake_http_content_length=False, *args):
        self.ip = ip
        self.port = port
        self.bridges = bridges
        self.message_queue = message_queue
        self.stream_manager = StreamManager(self)
        self.fake_http_content_length = fake_http_content_length

    def run(self):
        self.allow_reuse_address = True
        SocketServer.TCPServer.__init__(
            self, ('', self.port), StreamRequestHandler)

        setproctitle.setproctitle('stream_server')
        self.serve_forever()


class GobjectMainLoopMixin:

    def serve_forever(self, poll_interval=0.5):
        self.mainloop = gobject.MainLoop()
        if hasattr(self, 'socket'):
            gobject.io_add_watch(
                self, gobject.IO_IN | gobject.IO_PRI, self._on_new_request)
        context = self.mainloop.get_context()
        while True:
            try:
                if context.pending():
                    context.iteration(True)
                else:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                break

    def _on_new_request(self, sock, *args):
        self._handle_request_noblock()
        return True

    def shutdown(self, *args):
        logger.debug(
            'StreamServer GobjectMainLoopMixin.shutdown() pid: {}'.format(
                os.getpid()))
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except socket.error:
            pass
        self.socket.close()
        sys.exit(0)


class ThreadedStreamServer(
        GobjectMainLoopMixin, SocketServer.ThreadingMixIn, StreamServer):
    pass
