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

import SocketServer
import logging
import socket
import struct
import setproctitle
import time
import gobject
import os
import sys
import chardet

logger = logging.getLogger('pulseaudio_dlna.listener')


class SSDPRequestHandler(SocketServer.BaseRequestHandler):

    def handle(self):
        guess = chardet.detect(self.request[0])
        packet = self.request[0].decode(guess['encoding'])
        lines = packet.splitlines()
        if len(lines) > 0:
            if self._is_notify_method(lines[0]):
                logger.debug(
                    'Recieved the following NOTIFY header: \n{header}'.format(
                        header=packet))
                if self.server.holder:
                    self.server.holder.process_notify_request(packet)
            elif self._is_http_method(lines[0]):
                logger.debug(
                    'Recieved the following SSDP header: \n{header}'.format(
                        header=packet))
                if self.server.holder:
                    self.server.holder.process_msearch_request(packet)

    def _is_notify_method(self, method_header):
        method = self._get_method(method_header)
        return method == 'NOTIFY'

    def _is_http_method(self, method_header):
        method = self._get_method(method_header)
        return method in ['HTTP/0.9', 'HTTP/1.0', 'HTTP/1.1']

    def _get_method(self, method_header):
        return method_header.split(' ')[0]


class SSDPListener(SocketServer.UDPServer):

    SSDP_ADDRESS = '239.255.255.250'
    SSDP_PORT = 1900
    TTL = 10

    MSEARCH = 'M-SEARCH * HTTP/1.1\r\n' + \
              'HOST: {}:{}\r\n'.format(SSDP_ADDRESS, SSDP_PORT) + \
              'MAN: "ssdp:discover"\r\n' + \
              'MX: 2\r\n' + \
              'ST: ssdp:all\r\n\r\n'

    def __init__(
            self, holder=None, disable_ssdp_listener=False,
            disable_ssdp_search=False):
        self.disable_ssdp_listener = disable_ssdp_listener
        self.disable_ssdp_search = disable_ssdp_search
        self.holder = holder

        self.allow_reuse_address = True
        SocketServer.UDPServer.__init__(
            self, ('', self.SSDP_PORT), SSDPRequestHandler)
        self.socket.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_ADD_MEMBERSHIP,
            self._multicast_struct(self.SSDP_ADDRESS))
        self.socket.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_MULTICAST_TTL,
            self._ttl_struct(self.TTL))

        if not self.disable_ssdp_search:
            self.search()

    def _multicast_struct(self, address):
        return struct.pack(
            '=4sl', socket.inet_aton(address), socket.INADDR_ANY)

    def _ttl_struct(self, ttl):
        return struct.pack('=b', ttl)

    def search(self, times=4):
        for i in range(0, times):
            self.socket.sendto(
                self.MSEARCH, (self.SSDP_ADDRESS, self.SSDP_PORT))
            time.sleep(0.1)

    def _on_shutdown(self):
        logger.info('Discovery complete.')
        self.shutdown()
        return False

    def run(self):
        if self.disable_ssdp_listener:
            gobject.timeout_add(5000, self._on_shutdown)
        setproctitle.setproctitle('ssdp_listener')
        self.serve_forever(self)


class GobjectMainLoopMixin:

    def serve_forever(self, poll_interval=0.5):
        self.mainloop = gobject.MainLoop()
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
            'SSDPListener GobjectMainLoopMixin.shutdown() pid: {}'.format(
                os.getpid()))
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except socket.error:
            pass
        self.socket.close()
        sys.exit(0)


class ThreadedSSDPListener(
        GobjectMainLoopMixin, SocketServer.ThreadingMixIn, SSDPListener):
    pass
