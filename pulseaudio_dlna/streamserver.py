#!/usr/bin/python3

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

from gi.repository import GObject

import re
import subprocess
import setproctitle
import logging
import socket
import select
import sys
import base64
import urllib.parse
import json
import os
import signal
import pkg_resources
import http.server
import socketserver
import queue
import threading

import pulseaudio_dlna.encoders
import pulseaudio_dlna.codecs
import pulseaudio_dlna.recorders
import pulseaudio_dlna.rules
import pulseaudio_dlna.images

logger = logging.getLogger('pulseaudio_dlna.streamserver')

PROTOCOL_VERSION_V10 = 'HTTP/1.0'
PROTOCOL_VERSION_V11 = 'HTTP/1.1'


class ProcessQueue(queue.Queue):

    def data(self):
        data = self.get()
        if not self.empty():
            data = [data]
            while not self.empty():
                data.append(self.get())
            data = b''.join(data)
        return data


class ProcessThread(threading.Thread):

    CHUNK_SIZE = 1024 * 32

    def __init__(self, path, encoder, recorder, queue, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.path = path
        self.encoder = encoder
        self.recorder = recorder
        self.recorder_process = None
        self.encoder_process = None
        self.queue = queue

        self.reinitialize_count = 0
        self.stop_event = threading.Event()

        GObject.timeout_add(
            10000, self._on_regenerate_reinitialize_count)

    def _on_regenerate_reinitialize_count(self):
        if self.reinitialize_count > 0:
            self.reinitialize_count -= 1
        return True

    def stop(self):
        self.stop_event.set()

    @property
    def is_stopped(self):
        return self.stop_event.isSet()

    def run(self):

        def create_processes():
            logger.info('Starting processes "{recorder} | {encoder}"'.format(
                recorder=' '.join(self.recorder.command),
                encoder=' '.join(self.encoder.command)))
            rec_process = subprocess.Popen(
                self.recorder.command,
                stdout=subprocess.PIPE)
            enc_process = subprocess.Popen(
                self.encoder.command,
                stdin=rec_process.stdout,
                stdout=subprocess.PIPE,
                bufsize=-1)
            rec_process.stdout.close()
            return rec_process, enc_process, enc_process.stdout.read

        def do_processes_respond(rec_process, enc_process):
            return (rec_process.poll() is None and
                    enc_process.poll() is None)

        def terminate_processes(processes):
            for process in processes:
                pid = process.pid
                logger.debug('Terminating process {} ...'.format(pid))
                try:
                    os.kill(pid, signal.SIGTERM)
                    _pid, return_code = os.waitpid(pid, 0)
                except Exception:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except Exception:
                        pass

        chunk_size = self.CHUNK_SIZE
        queue = self.queue

        rec_process, enc_process, enc_read = create_processes()
        logger.info(
            'Processes of {path} initialized ...'.format(
                path=self.path))
        while not self.is_stopped:
            if not do_processes_respond(rec_process, enc_process):
                if self.reinitialize_count < 3:
                    self.reinitialize_count += 1
                    terminate_processes([rec_process, enc_process])
                    rec_process, enc_process, enc_read = create_processes()
                    logger.info(
                        'Processes of {path} reinitialized ...'.format(
                            path=self.path))
                else:
                    logger.error(
                        'There were more than {} attempts to reinitialize '
                        'the record process. Aborting.'.format(
                            self.reinitialize_count))
                    break

            data = enc_read(chunk_size)
            if len(data) > 0:
                queue.put(data)

        terminate_processes([rec_process, enc_process])
        queue.put(b'')


class ProcessStream(object):

    RUNNING = True

    def __init__(self, path, sock, recorder, encoder, bridge):
        self.path = path
        self.sock = sock
        self.recorder = recorder
        self.encoder = encoder
        self.bridge = bridge

        self.id = hex(id(self))

    def run(self):

        queue = ProcessQueue()
        process_thread = ProcessThread(
            self.path, self.encoder, self.recorder, queue)
        process_thread.daemon = True
        process_thread.start()

        empty_list = []
        select_select = select.select
        sock = self.sock
        sock_list = [self.sock]
        sock_sendall = self.sock.sendall
        sock_recv = self.sock.recv
        queue_data = queue.data

        while self.RUNNING:
            r, w, e = select_select(sock_list, sock_list, empty_list, 0)

            if sock in w:
                data = queue_data()
                if len(data) == 0:
                    break
                try:
                    sock_sendall(data)
                except socket.error:
                    break

            if sock in r:
                try:
                    data = sock_recv(1024)
                    if len(data) == 0:
                        break
                except socket.error:
                    break

        process_thread.stop()

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
        logger.info('Registered stream "{}" ({}) ...'.format(
            stream.path, stream.id))
        if not self.streams.get(stream.path, None):
            self.streams[stream.path] = {}
        self.streams[stream.path][stream.id] = stream

    def unregister(self, stream):
        logger.info('Unregistered stream "{}" ({}) ...'.format(
            stream.path, stream.id))
        del self.streams[stream.path][stream.id]

        if stream.path in self.timeouts:
            GObject.source_remove(self.timeouts[stream.path])
        self.timeouts[stream.path] = GObject.timeout_add(
            2000, self._on_disconnect, stream)

    def _on_disconnect(self, stream):
        self.timeouts.pop(stream.path)
        if len(self.streams[stream.path]) == 0:
            logger.info('No more stream from device "{}".'.format(
                stream.bridge.device.name))
            self.server.pulse_queue.put({
                'type': 'on_bridge_disconnected',
                'stopped_bridge': stream.bridge,
            })

    def __str__(self):
        return '<{}>\n{}\n'.format(
            self.__class__.__name__,
            '\n'.join(
                ['    {}\n        {}'.format(
                    path,
                    '        '.join(
                        [str(s) for id, s in list(streams.items())]))
                    for path, streams in list(self.streams.items())],
            ),
        )


class StreamRequestHandler(http.server.BaseHTTPRequestHandler):
    def __init__(self, *args):
        try:
            http.server.BaseHTTPRequestHandler.__init__(self, *args)
        except IOError:
            pass

    def do_HEAD(self):
        logger.debug('Got the following HEAD request:\n{header}'.format(
            header=json.dumps(list(self.headers.items()), indent=2)))
        item = self.get_requested_item()
        self.handle_headers(item)

    def do_GET(self):
        logger.debug('Got the following GET request:\n{header}'.format(
            header=json.dumps(list(self.headers.items()), indent=2)))
        item = self.get_requested_item()
        self.handle_headers(item)
        if isinstance(item, pulseaudio_dlna.images.BaseImage):
            self.wfile.write(item.data)
        elif isinstance(item, pulseaudio_dlna.pulseaudio.PulseBridge):
            self.server.stream_manager.create_stream(
                self.path, self.request, item)

    def handle_headers(self, item):
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
            bridge = item
            headers['Content-Type'] = bridge.device.codec.specific_mime_type

            if self.server.fake_http_content_length or \
               pulseaudio_dlna.rules.FAKE_HTTP_CONTENT_LENGTH in \
               bridge.device.codec.rules:
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
                    pulseaudio_dlna.plugins.dlna.renderer.DLNAMediaRenderer):
                headers['contentFeatures.dlna.org'] = str(
                    bridge.device.content_features)
                headers['Ext'] = ''
                headers['transferMode.dlna.org'] = 'Streaming'
                headers['Content-Disposition'] = 'inline;'

        logger.debug('Sending header ({response_code}):\n{header}'.format(
            response_code=response_code,
            header=json.dumps(headers, indent=2),
        ))
        self.send_response(response_code)
        for name, value in list(headers.items()):
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
                        'images', os.path.basename(image_name)))
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
                        os.path.basename(icon_name), size=512)
                except (pulseaudio_dlna.images.UnknownImageExtension,
                        pulseaudio_dlna.images.ImageNotAccessible,
                        pulseaudio_dlna.images.MissingDependencies,
                        pulseaudio_dlna.images.IconNotFound) as e:
                    logger.error(e)
        return None

    def _decode_settings(self, path):
        try:
            data_quoted = re.findall(r'/(.*?)/', path)[0]
            data_bytes = base64.b64decode(urllib.parse.unquote(data_quoted))
            data_string = data_bytes.decode()
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
        pass


class StreamServer(socketserver.TCPServer):

    HOST = None
    PORT = None

    def __init__(
            self, ip, port, pulse_queue, stream_queue,
            fake_http_content_length=False, proc_title=None, *args):
        self.ip = ip or self.HOST
        self.port = port or self.PORT
        self.pulse_queue = pulse_queue
        self.stream_queue = stream_queue
        self.stream_manager = StreamManager(self)
        self.fake_http_content_length = fake_http_content_length
        self.proc_title = proc_title
        self.bridges = []

    def run(self):
        self.allow_reuse_address = True
        self.daemon_threads = True
        try:
            socketserver.TCPServer.__init__(
                self, (self.ip or '', self.port), StreamRequestHandler)
        except socket.error:
            logger.critical(
                'The streaming server could not bind to your specified port '
                '({port}). Perhaps this is already in use? The application '
                'cannot work properly!'.format(port=self.port))
            sys.exit(1)

        signal.signal(signal.SIGTERM, self.shutdown)
        if self.proc_title:
            setproctitle.setproctitle(self.proc_title)
        self.serve_forever()

    def update_bridges(self, bridges):
        self.bridges = bridges


class GobjectMainLoopMixin:

    def serve_forever(self, poll_interval=0.5):
        mainloop = GObject.MainLoop()
        if hasattr(self, 'socket'):
            GObject.io_add_watch(
                self, GObject.IO_IN | GObject.IO_PRI, self._on_new_request)
        if hasattr(self, 'stream_queue'):
            GObject.io_add_watch(
                self.stream_queue._reader, GObject.IO_IN | GObject.IO_PRI,
                self._on_new_message)
        try:
            mainloop.run()
        except KeyboardInterrupt:
            self.shutdown()

    def _on_new_message(self, fd, condition):
        try:
            message = self.stream_queue.get_nowait()
        except Exception:
            return True

        message_type = message.get('type', None)
        if message_type and hasattr(self, message_type):
            del message['type']
            getattr(self, message_type)(**message)
        return True

    def _on_new_request(self, sock, *args):
        self._handle_request_noblock()
        return True

    def shutdown(self, *args):
        logger.info(
            'StreamServer GobjectMainLoopMixin.shutdown()')
        ProcessStream.RUNNING = False
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except socket.error:
            pass
        self.socket.close()
        sys.exit(0)


class ThreadedStreamServer(
        GobjectMainLoopMixin, socketserver.ThreadingMixIn, StreamServer):
    pass
