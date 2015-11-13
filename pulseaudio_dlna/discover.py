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

import socket as s
import logging
import time
import chardet
import struct

logger = logging.getLogger('pulseaudio_dlna.discover')


class BaseUpnpMediaRendererDiscover(object):

    SSDP_ADDRESS = '239.255.255.250'
    SSDP_PORT = 1900
    SSDP_MX = 2
    SSDP_TTL = 10
    SSDP_AMOUNT = 5

    MSEARCH = 'M-SEARCH * HTTP/1.1\r\n' + \
              'HOST: {}:{}\r\n'.format(SSDP_ADDRESS, SSDP_PORT) + \
              'MAN: "ssdp:discover"\r\n' + \
              'MX: 2\r\n' + \
              'ST: ssdp:all\r\n\r\n'

    def search(self, ssdp_ttl=None, ssdp_mx=None, ssdp_amount=None):
        ssdp_mx = ssdp_mx or self.SSDP_MX
        ssdp_ttl = ssdp_ttl or self.SSDP_TTL
        ssdp_amount = ssdp_amount or self.SSDP_AMOUNT

        s.setdefaulttimeout(ssdp_mx + 2)
        sock = s.socket(s.AF_INET, s.SOCK_DGRAM, s.IPPROTO_UDP)
        sock.setsockopt(s.SOL_SOCKET, s.SO_REUSEADDR, 1)
        sock.bind(('', self.SSDP_PORT))
        sock.setsockopt(
            s.IPPROTO_IP,
            s.IP_ADD_MEMBERSHIP,
            self._multicast_struct(self.SSDP_ADDRESS))
        sock.setsockopt(
            s.IPPROTO_IP,
            s.IP_MULTICAST_TTL,
            self._ttl_struct(ssdp_ttl))

        msg = 'M-SEARCH * HTTP/1.1\r\n' + \
              'HOST: {}:{}\r\n'.format(self.SSDP_ADDRESS, self.SSDP_PORT) + \
              'MAN: "ssdp:discover"\r\n' + \
              'MX: {}\r\n'.format(ssdp_mx) + \
              'ST: ssdp:all\r\n\r\n'
        for i in range(0, ssdp_amount):
            sock.sendto(msg, (self.SSDP_ADDRESS, self.SSDP_PORT))
            time.sleep(0.1)

        buffer_size = 1024
        while True:
            try:
                header, address = sock.recvfrom(buffer_size)
                guess = chardet.detect(header)
                self._header_received(
                    header.decode(guess['encoding']), address)
            except s.timeout:
                break
        sock.close()

    def _multicast_struct(self, address):
        return struct.pack('=4sl', s.inet_aton(address), s.INADDR_ANY)

    def _ttl_struct(self, ttl):
        return struct.pack('=b', ttl)

    def _header_received(self, header, address):
        pass


class RendererDiscover(BaseUpnpMediaRendererDiscover):

    def __init__(self, renderer_holder):
        self.renderer_holder = renderer_holder

    def search(self, *args, **kwargs):
        self.renderers = []
        BaseUpnpMediaRendererDiscover.search(self, *args, **kwargs)

    def _header_received(self, header, address):
        logger.debug('Recieved the following SSDP header: \n{header}'.format(
            header=header))
        self.renderer_holder.process_msearch_request(header)
