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

import socket
import logging
import chardet
import threading

logger = logging.getLogger('pulseaudio_dlna.discover')


class SSDPDiscover(object):

    SSDP_ADDRESS = '239.255.255.250'
    SSDP_PORT = 1900
    SSDP_MX = 2
    SSDP_TTL = 10
    SSDP_AMOUNT = 5

    BUFFER_SIZE = 1024
    MSEARCH = '\r\n'.join([
        'M-SEARCH * HTTP/1.1',
        'HOST: {host}:{port}',
        'MAN: "ssdp:discover"',
        'MX: {mx}',
        'ST: ssdp:all',
    ]) + '\r\n' * 2

    def search(self, ssdp_ttl=None, ssdp_mx=None, ssdp_amount=None):
        ssdp_mx = ssdp_mx or self.SSDP_MX
        ssdp_ttl = ssdp_ttl or self.SSDP_TTL
        ssdp_amount = ssdp_amount or self.SSDP_AMOUNT

        sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(ssdp_mx + 2)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_MULTICAST_TTL,
            ssdp_ttl)
        sock.bind(('', self.SSDP_PORT))

        for i in range(1, ssdp_amount + 1):
            t = threading.Timer(
                float(i) / 2, self._send_discover, args=[sock, ssdp_mx])
            t.start()

        self._listen(sock)
        sock.close()

    def _listen(self, sock):
        while True:
            try:
                header, address = sock.recvfrom(self.BUFFER_SIZE)
                guess = chardet.detect(header)
                self._header_received(
                    header.decode(guess['encoding']), address)
            except socket.timeout:
                break

    def _send_discover(self, sock, ssdp_mx):
        msg = self.MSEARCH.format(
            host=self.SSDP_ADDRESS, port=self.SSDP_PORT, mx=ssdp_mx)
        sock.sendto(msg, (self.SSDP_ADDRESS, self.SSDP_PORT))

    def _header_received(self, header, address):
        pass


class RendererDiscover(SSDPDiscover):

    def __init__(self, renderer_holder):
        SSDPDiscover.__init__(self)
        self.renderer_holder = renderer_holder

    def search(self, *args, **kwargs):
        self.renderers = []
        SSDPDiscover.search(self, *args, **kwargs)

    def _header_received(self, header, address):
        logger.debug('Recieved the following SSDP header: \n{header}'.format(
            header=header))
        self.renderer_holder.process_msearch_request(header)
