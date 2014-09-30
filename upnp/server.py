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

import sys
import subprocess
import logging
import errno
import BaseHTTPServer
import SocketServer


class DlnaRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    def __init__(self, *args):
        try:
            BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, *args)
        except IOError as e:
            if e.errno == errno.EPIPE:
                logging.info('stream closed.')

    def do_HEAD(self):
        self.send_response(200)
        self.send_header('Content-Type', self.server.encoder_mime)
        self.end_headers()

    def do_GET(self):
        self.do_HEAD()
        for bridge in self.server.bridges:
            if self.path == bridge.upnp_device.stream_name:
                logging.info('starting sending stream to "{}"'.format(
                    bridge.upnp_device.name))
                recorder_process = subprocess.Popen(
                    self.server.recorder_cmd.format(
                        bridge.sink.monitor).split(' '),
                    stdout=subprocess.PIPE)
                encoder_process = subprocess.Popen(
                    self.server.encoder_cmd.split(' '),
                    stdin=recorder_process.stdout,
                    stdout=subprocess.PIPE)
                recorder_process.stdout.close()
                while True:
                    stream_data = encoder_process.stdout.read(1024)
                    if len(stream_data) == 0:
                        break
                    self.wfile.write(stream_data)
                return
        logging.info('error 404: file not found "{}"'.format(self.path))
        self.send_error(404, 'file not found: %s' % self.path)


class DlnaServer(SocketServer.TCPServer):

    ENCODER_LAME = 'lame'
    ENCODER_FLAC = 'flac'
    ENCODER_OGG = 'ogg'
    ENCODER_WAV = 'wav'
    RECORDER_PULSEAUDIO = 'pulseaudio'

    def __init__(self, ip, port, recorder=None, encoder=None, *args):
        SocketServer.TCPServer.allow_reuse_address = True
        SocketServer.TCPServer.__init__(
            self, ('', port), DlnaRequestHandler, *args)

        self.ip = ip
        self.port = port
        self.recorder_cmd = None
        self.encoder_cmd = None
        self.encoder_mime = None
        self.bridges = []

        self.encoders = [
            self.ENCODER_LAME,
            self.ENCODER_FLAC,
            self.ENCODER_OGG,
            self.ENCODER_WAV,
        ]

        self.set_recorder()
        self.set_encoder(encoder)

    def get_server_url(self):
        return 'http://{ip}:{port}'.format(
            ip=self.ip,
            port=self.port,
        )

    def set_bridges(self, bridges):
        self.bridges = bridges

    def set_recorder(self, type_=None):
        type_ = type_ or self.RECORDER_PULSEAUDIO
        if type_ == self.RECORDER_PULSEAUDIO:
            self.recorder_cmd = 'parec --format=s16le -d {}'

    def set_encoder(self, type_=None):
        type_ = type_ or self.ENCODER_LAME
        if type_ not in self.encoders:
            logging.error('You specified an encoder which does not exists!')
            sys.exit(1)
        if type_ == self.ENCODER_LAME:
            self.encoder_cmd = 'lame -r -b 320 -'
            self.encoder_mime = 'audio/mpeg'
        if type_ == self.ENCODER_FLAC:
            self.encoder_cmd = 'flac - -c --channels 2 --bps 16 --sample-rate 44100 --endian little --sign signed'
            self.encoder_mime = 'audio/flac'
        if type_ == self.ENCODER_OGG:
            self.encoder_cmd = 'oggenc -r -'
            self.encoder_mime = 'audio/ogg'
        if type_ == self.ENCODER_WAV:
            self.encoder_cmd = 'sox -t raw -b 16 -e signed -c 2 -r 44100 - -t wav -r 44100 -b 16 -L -e signed -c 2 -'
            self.encoder_mime = 'audio/wav'


class ThreadedDlnaServer(SocketServer.ThreadingMixIn, DlnaServer):
    pass
