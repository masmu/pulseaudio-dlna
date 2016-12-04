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
import chardet

import pulseaudio_dlna.plugins.upnp.ssdp

logger = logging.getLogger('pulseaudio_dlna.plugins.upnp.ssdp')


class SSDPHandler(SocketServer.BaseRequestHandler):

    SSDP_ALIVE = 'ssdp:alive'
    SSDP_BYEBYE = 'ssdp:byebye'

    def handle(self):
        packet = self._decode(self.request[0])
        lines = packet.splitlines()
        if len(lines) > 0:
            if self._is_notify_method(lines[0]):
                header = pulseaudio_dlna.plugins.upnp.ssdp._get_header_map(
                    packet)
                nts_header = header.get('nts', None)
                if nts_header and nts_header == self.SSDP_ALIVE:
                    if self.server.cb_on_device_alive:
                        self.server.cb_on_device_alive(header)
                elif nts_header and nts_header == self.SSDP_BYEBYE:
                    if self.server.cb_on_device_byebye:
                        self.server.cb_on_device_byebye(header)

    def _decode(self, data):
        guess = chardet.detect(data)
        for encoding in [guess['encoding'], 'utf-8', 'ascii']:
            try:
                return data.decode(encoding)
            except:
                pass
        logger.error('Could not decode SSDP packet.')
        return ''

    def _is_notify_method(self, method_header):
        method = self._get_method(method_header)
        return method == 'NOTIFY'

    def _get_method(self, method_header):
        return method_header.split(' ')[0]


class SSDPListener(SocketServer.UDPServer):

    SSDP_ADDRESS = '239.255.255.250'
    SSDP_PORT = 1900
    SSDP_TTL = 10

    DISABLE_SSDP_LISTENER = False

    def __init__(self, cb_on_device_alive=None, cb_on_device_byebye=None,
                 host=None):
        self.cb_on_device_alive = cb_on_device_alive
        self.cb_on_device_byebye = cb_on_device_byebye
        self.host = host

    def run(self, ttl=None):
        if self.DISABLE_SSDP_LISTENER:
            return

        self.allow_reuse_address = True
        SocketServer.UDPServer.__init__(
            self, (self.host or '', self.SSDP_PORT), SSDPHandler)
        self.socket.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_ADD_MEMBERSHIP,
            self._multicast_struct(self.SSDP_ADDRESS))
        self.socket.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_MULTICAST_TTL,
            self.SSDP_TTL)

        if ttl:
            gobject.timeout_add(ttl * 1000, self.shutdown)

        setproctitle.setproctitle('ssdp_listener')
        self.serve_forever(self)
        logger.debug('SSDPListener.run() quit')

    def _multicast_struct(self, address):
        return struct.pack(
            '4sl', socket.inet_aton(address), socket.INADDR_ANY)


class GobjectMainLoopMixin:

    def serve_forever(self, poll_interval=0.5):
        self.__running = False
        self.__mainloop = gobject.MainLoop()

        if hasattr(self, 'socket'):
            gobject.io_add_watch(
                self, gobject.IO_IN | gobject.IO_PRI, self._on_new_request)

        context = self.__mainloop.get_context()
        while not self.__running:
            try:
                if context.pending():
                    context.iteration(True)
                else:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                break
        logger.debug('SSDPListener.serve_forever() quit')

    def _on_new_request(self, sock, *args):
        self._handle_request_noblock()
        return True

    def shutdown(self, *args):
        logger.debug('SSDPListener.shutdown()')
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except socket.error:
            pass
        self.__running = True
        self.server_close()


class ThreadedSSDPListener(
        GobjectMainLoopMixin, SocketServer.ThreadingMixIn, SSDPListener):
    pass
