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
import setproctitle
import logging
import time
import socket
import select
import sys
import gobject
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


def time_log(method, point=None):
    logger.info('{time} - {method}() - {point}'.format(
        time=time.time(), method=method, point=point or ''))


class ProcessStream(object):
    def __init__(self, path, sock, recorder, encoder, bridge):
        time_log('ProcessStream.__init__')
        self.path = path
        self.sock = sock
        self.recorder = recorder
        self.encoder = encoder
        self.bridge = bridge

        self.id = hex(id(self))
        self.recorder_process = None
        self.encoder_process = None
        self.chunk_size = 1024 * 4
        self.reinitialize_count = 0

        gobject.timeout_add(
            10000, self._on_regenerate_reinitialize_count)

    def run(self):
        time_log('ProcessStream.run')
        while True:
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
            r, w, e = select.select([self.sock], [self.sock], [], 0)

            if self.sock in w:
                try:
                    self._send_data(self.sock, data)
                except socket.error:
                    break

            if self.sock in r:
                try:
                    data = self.sock.recv(1024)
                    if len(data) == 0:
                        break
                except socket.error:
                    break
        self.terminate_processes()

    def _send_data(self, sock, data):
        bytes_total = len(data)
        bytes_sent = 0
        while bytes_sent < bytes_total:
            bytes_sent += sock.send(data[bytes_sent:])

    def _on_regenerate_reinitialize_count(self):
        time_log('ProcessStream._on_regenerate_reinitialize_count')
        if self.reinitialize_count > 0:
            self.reinitialize_count -= 1
        return True

    def do_processes_exist(self):
        return (self.encoder_process is not None and
                self.recorder_process is not None)

    def do_processes_respond(self):
        return (self.recorder_process.poll() is None and
                self.encoder_process.poll() is None)

    def terminate_processes(self):
        time_log('ProcessStream.terminate_processes')

        def _kill_process(process):
            pid = process.pid
            logger.debug('Terminating process {} ...'.format(pid))
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
        time_log('ProcessStream.create_processes')
        if self.reinitialize_count < 3:
            self.reinitialize_count += 1
            logger.info('Starting processes "{recorder} | {encoder}"'.format(
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
            logger.error('There were more than {} attempts to reinitialize '
                         'the record process. Aborting.'.format(
                             self.reinitialize_count))

    def __str__(self):
        return '<{} id="{}">\n'.format(
            self.__class__.__name__,
            self.id,
        )


class StreamManager(object):
    def __init__(self, server):
        self.streams = {}
        self.timeouts = {}
        self.server = server

    def create_stream(self, path, request, bridge):
        time_log('StreamManager.create_stream')
        stream = ProcessStream(
            path=path,
            sock=request,
            recorder=bridge.device.codec.get_recorder(bridge.sink.monitor),
            encoder=bridge.device.codec.encoder,
            bridge=bridge,
        )
        self.register(stream)
        stream.run()
        self.unregister(stream)

    def register(self, stream):
        time_log('StreamManager.register')
        logger.info('Registered stream "{}" ({}) ...'.format(
            stream.path, stream.id))
        if not self.streams.get(stream.path, None):
            self.streams[stream.path] = {}
        self.streams[stream.path][stream.id] = stream

    def unregister(self, stream):
        time_log('StreamManager.unregister')
        logger.info('Unregistered stream "{}" ({}) ...'.format(
            stream.path, stream.id))
        del self.streams[stream.path][stream.id]

        if stream.path in self.timeouts:
            gobject.source_remove(self.timeouts[stream.path])
        self.timeouts[stream.path] = gobject.timeout_add(
            2000, self._on_disconnect, stream)

    def _on_disconnect(self, stream):
        time_log('StreamManager._on_disconnect')
        self.timeouts.pop(stream.path)
        if len(self.streams[stream.path]) == 0:
            logger.info('No more stream from device "{}".'.format(
                stream.bridge.device.name))
            self.server.message_queue.put({
                'type': 'on_bridge_disconnected',
                'stopped_bridge': stream.bridge,
            })

    def __str__(self):
        return '<{}>\n{}\n'.format(
            self.__class__.__name__,
            '\n'.join(
                ['    {}\n        {}'.format(
                    path,
                    '        '.join([str(s) for id, s in streams.items()]))
                    for path, streams in self.streams.items()],
            ),
        )


class StreamRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def __init__(self, *args):
        time_log('StreamRequestHandler.__init__')
        try:
            BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *args)
        except IOError:
            pass

    def do_HEAD(self):
        time_log('StreamRequestHandler.do_HEAD')
        logger.debug('Got the following HEAD request:\n{header}'.format(
            header=json.dumps(self.headers.items(), indent=2)))
        item = self.get_requested_item()
        self.handle_headers(item)

    def do_GET(self):
        time_log('StreamRequestHandler.do_GET')
        logger.debug('Got the following GET request:\n{header}'.format(
            header=json.dumps(self.headers.items(), indent=2)))
        item = self.get_requested_item()
        self.handle_headers(item)
        if isinstance(item, pulseaudio_dlna.images.BaseImage):
            self.wfile.write(item.data)
        elif isinstance(item, pulseaudio_dlna.pulseaudio.PulseBridge):
            self.server.stream_manager.create_stream(
                self.path, self.request, item)

    def handle_headers(self, item):
        time_log('StreamRequestHandler.handle_headers')
        response_code = 200
        headers = {}

        if not item:
            logger.info('Requested file not found "{}"'.format(self.path))
            self.send_error(404, 'File not found: %s' % self.path)
            return
        elif isinstance(item, pulseaudio_dlna.images.BaseImage):
            image = item
            headers['Content-Type'] = image.content_type
        elif isinstance(item, pulseaudio_dlna.pulseaudio.PulseBridge):
            time_log('StreamRequestHandler.handle_headers', 1)
            bridge = item
            headers['Content-Type'] = bridge.device.codec.specific_mime_type

            time_log('StreamRequestHandler.handle_headers', 2)
            if self.server.fake_http_content_length or \
               pulseaudio_dlna.rules.FAKE_HTTP_CONTENT_LENGTH in \
               bridge.device.codec.rules:
                time_log('StreamRequestHandler.handle_headers', 31)
                gb_in_bytes = pow(1024, 3)
                headers['Content-Length'] = gb_in_bytes * 100
                time_log('StreamRequestHandler.handle_headers', 32)
            else:
                time_log('StreamRequestHandler.handle_headers', 4)
                if self.request_version == PROTOCOL_VERSION_V10:
                    pass
                elif self.request_version == PROTOCOL_VERSION_V11:
                    headers['Connection'] = 'close'
                time_log('StreamRequestHandler.handle_headers', 5)

            if self.headers.get('range'):
                time_log('StreamRequestHandler.handle_headers', 6)
                match = re.search(
                    'bytes=(\d+)-(\d+)?', self.headers['range'], re.IGNORECASE)
                time_log('StreamRequestHandler.handle_headers', 61)
                if match:
                    time_log('StreamRequestHandler.handle_headers', 62)
                    start_range = int(match.group(1))
                    time_log('StreamRequestHandler.handle_headers', 63)
                    if start_range != 0:
                        time_log('StreamRequestHandler.handle_headers', 64)
                        response_code = 206

            if isinstance(
                bridge.device,
                    pulseaudio_dlna.plugins.upnp.renderer.UpnpMediaRenderer):
                time_log('StreamRequestHandler.handle_headers', 7)
                content_features = UpnpContentFeatures(
                    flags=[
                        UpnpContentFlags.STREAMING_TRANSFER_MODE_SUPPORTED,
                        UpnpContentFlags.BACKGROUND_TRANSFER_MODE_SUPPORTED,
                        UpnpContentFlags.CONNECTION_STALLING_SUPPORTED,
                        UpnpContentFlags.DLNA_VERSION_15_SUPPORTED
                    ])
                time_log('StreamRequestHandler.handle_headers', 71)
                headers['contentFeatures.dlna.org'] = str(content_features)
                headers['Ext'] = ''
                headers['transferMode.dlna.org'] = 'Streaming'
                headers['Content-Disposition'] = 'inline;'
                time_log('StreamRequestHandler.handle_headers', 72)

        logger.debug('Sending header ({response_code}):\n{header}'.format(
            response_code=response_code,
            header=json.dumps(headers, indent=2),
        ))
        time_log('StreamRequestHandler.handle_headers', 8)
        self.send_response(response_code)
        for name, value in headers.items():
            time_log('StreamRequestHandler.handle_headers', 81)
            self.send_header(name, value)
        time_log('StreamRequestHandler.handle_headers', 82)
        self.end_headers()
        time_log('StreamRequestHandler.handle_headers', 83)

    def get_requested_item(self):
        time_log('StreamRequestHandler.get_requested_item')
        settings = self._decode_settings(self.path)
        time_log('StreamRequestHandler.get_requested_item', 1)
        if settings.get('type', None) == 'bridge':
            time_log('StreamRequestHandler.get_requested_item', 2)
            for bridge in self.server.bridges:
                if settings.get('udn') == bridge.device.udn:
                    time_log('StreamRequestHandler.get_requested_item', 21)
                    return bridge
        elif settings.get('type', None) == 'image':
            time_log('StreamRequestHandler.get_requested_item', 3)
            image_name = settings.get('name', None)
            if image_name:
                time_log('StreamRequestHandler.get_requested_item', 31)
                image_path = pkg_resources.resource_filename(
                    'pulseaudio_dlna.streamserver', os.path.join(
                        'images', os.path.basename(image_name)))
                time_log('StreamRequestHandler.get_requested_item', 32)
                try:
                    time_log('StreamRequestHandler.get_requested_item', 33)
                    _type = pulseaudio_dlna.images.get_type_by_filepath(
                        image_path)
                    time_log('StreamRequestHandler.get_requested_item', 34)
                    return _type(path=image_path, cached=True)
                except (pulseaudio_dlna.images.UnknownImageExtension,
                        pulseaudio_dlna.images.ImageNotAccessible,
                        pulseaudio_dlna.images.MissingDependencies,
                        pulseaudio_dlna.images.IconNotFound) as e:
                    time_log('StreamRequestHandler.get_requested_item', 35)
                    logger.error(e)
        elif settings.get('type', None) == 'sys-icon':
            time_log('StreamRequestHandler.get_requested_item', 4)
            icon_name = settings.get('name', None)
            if icon_name:
                time_log('StreamRequestHandler.get_requested_item', 41)
                try:
                    time_log('StreamRequestHandler.get_requested_item', 42)
                    return pulseaudio_dlna.images.get_icon_by_name(
                        os.path.basename(icon_name), size=512)
                except (pulseaudio_dlna.images.UnknownImageExtension,
                        pulseaudio_dlna.images.ImageNotAccessible,
                        pulseaudio_dlna.images.MissingDependencies,
                        pulseaudio_dlna.images.IconNotFound) as e:
                    time_log('StreamRequestHandler.get_requested_item', 43)
                    logger.error(e)
        return None

    def _decode_settings(self, path):
        time_log('StreamRequestHandler._decode_settings')
        try:
            time_log('StreamRequestHandler._decode_settings', 1)
            data_quoted = re.findall(r'/(.*?)/', path)[0]
            time_log('StreamRequestHandler._decode_settings', 2)
            data_string = base64.b64decode(urllib.unquote(data_quoted))
            time_log('StreamRequestHandler._decode_settings', 3)
            settings = {
                k: v for k, v in re.findall('(.*?)="(.*?)",?', data_string)
            }
            time_log('StreamRequestHandler._decode_settings', 4)
            logger.info(
                'URL settings: {path} ({data_string})'.format(
                    path=path,
                    data_string=data_string))
            time_log('StreamRequestHandler._decode_settings', 5)
            return settings
        except (TypeError, ValueError, IndexError):
            pass
        return {}

    def log_message(self, format, *args):
        time_log('StreamRequestHandler.log_message', 1)
        args = [unicode(arg) for arg in args]
        time_log('StreamRequestHandler.log_message', 2)
        logger.info('Got request from {host} - {args}' .format(
            host=self.address_string(),
            time=self.log_date_time_string(),
            args=','.join(args)))
        args = time_log('StreamRequestHandler.log_message', 3)


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
            self, (self.ip or '', self.port), StreamRequestHandler)

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
