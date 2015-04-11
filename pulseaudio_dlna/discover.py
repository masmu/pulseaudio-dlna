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
import re


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
                self._header_received(header, address)
            except s.timeout:
                break
        sock.close()

    def _header_received(self, header, address):
        pass


class RendererDiscover(BaseUpnpMediaRendererDiscover):

    def __init__(self, device_filter=None):
        self.renderers = None
        self.registered = {}
        self.device_filter = device_filter

    def register(self, identifier, _type):
        self.registered[identifier] = _type

    def search(self, ttl=10, timeout=5, times=2):
        self.renderers = []
        BaseUpnpMediaRendererDiscover.search(self, ttl, timeout, times)

    def _header_received(self, header, address):
        header = re.findall(r"(?P<name>.*?): (?P<value>.*?)\r\n", header)
        header = {k.lower(): v for k, v in dict(header).items()}
        if 'st' in header:
            st_header = header['st']
            if st_header in self.registered:
                device = self.registered[st_header].create_device(header)
                if device is not None:
                    if self.device_filter is None:
                        self._add_renderer(device)
                    else:
                        if device.name in self.device_filter:
                            self._add_renderer(device)
                        else:
                            logging.info('Skipped the device "{name}."'.format(
                                name=device.name))

    def _add_renderer(self, device):
        if device not in self.renderers:
            self.renderers.append(device)
