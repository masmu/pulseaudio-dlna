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

logger = logging.getLogger('pulseaudio_dlna.discover')


class BaseUpnpMediaRendererDiscover(object):

    SSDP_ADDRESS = '239.255.255.250'
    SSDP_PORT = 1900

    MSEARCH = 'M-SEARCH * HTTP/1.1\r\n' + \
              'HOST: {}:{}\r\n'.format(SSDP_ADDRESS, SSDP_PORT) + \
              'MAN: "ssdp:discover"\r\n' + \
              'MX: 2\r\n' + \
              'ST: ssdp:all\r\n\r\n'

    def search(self, ttl=10, timeout=5, times=4):
        s.setdefaulttimeout(timeout)
        sock = s.socket(s.AF_INET, s.SOCK_DGRAM, s.IPPROTO_UDP)
        sock.setsockopt(s.IPPROTO_IP, s.IP_MULTICAST_TTL, ttl)

        for i in range(0, times):
            sock.sendto(self.MSEARCH, (self.SSDP_ADDRESS, self.SSDP_PORT))
            time.sleep(0.1)

        buffer_size = 1024
        while True:
            try:
                header, address = sock.recvfrom(buffer_size)
                guess = chardet.detect(header)
                logger.info(guess)
                self._header_received(header.decode(guess['encoding']), address)
            except s.timeout:
                break
        sock.close()

    def _header_received(self, header, address):
        pass


class RendererDiscover(BaseUpnpMediaRendererDiscover):

    def __init__(self, renderer_holder):
        self.renderer_holder = renderer_holder

    def search(self, ttl=10, timeout=5, times=2):
        self.renderers = []
        BaseUpnpMediaRendererDiscover.search(self, ttl, timeout, times)

    def _header_received(self, header, address):
        logger.debug('Recieved the following SSDP header: \n{header}'.format(
            header=header))
        self.renderer_holder.add_from_search(header)
