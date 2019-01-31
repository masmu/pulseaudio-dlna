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

import socket
import logging
import chardet
import threading
import traceback

import pulseaudio_dlna.utils.network
import pulseaudio_dlna.plugins.dlna.ssdp

logger = logging.getLogger('pulseaudio_dlna.discover')


class SSDPDiscover(object):

    SSDP_ADDRESS = '239.255.255.250'
    SSDP_PORT = 1900
    SSDP_MX = 3
    SSDP_TTL = 10
    SSDP_AMOUNT = 5

    MSEARCH_PORT = 0
    MSEARCH_MSG = '\r\n'.join([
        'M-SEARCH * HTTP/1.1',
        'HOST: {host}:{port}',
        'MAN: "ssdp:discover"',
        'MX: {mx}',
        'ST: ssdp:all',
    ]) + '\r\n' * 2

    BUFFER_SIZE = 1024
    USE_SINGLE_SOCKET = True

    def __init__(self, cb_on_device_response, host=None):
        self.cb_on_device_response = cb_on_device_response
        self.host = host
        self.addresses = []

        self.refresh_addresses()

    def refresh_addresses(self):
        self.addresses = pulseaudio_dlna.utils.network.ipv4_addresses()

    def search(self, ssdp_ttl=None, ssdp_mx=None, ssdp_amount=None):
        ssdp_mx = ssdp_mx or self.SSDP_MX
        ssdp_ttl = ssdp_ttl or self.SSDP_TTL
        ssdp_amount = ssdp_amount or self.SSDP_AMOUNT

        if self.USE_SINGLE_SOCKET:
            self._search(self.host or '', ssdp_ttl, ssdp_mx, ssdp_amount)
        else:
            if self.host:
                self._search(self.host, ssdp_ttl, ssdp_mx, ssdp_amount)
            else:
                threads = []
                for addr in self.addresses:
                    thread = threading.Thread(
                        target=self._search,
                        args=[addr, ssdp_ttl, ssdp_mx, ssdp_amount])
                    threads.append(thread)
                try:
                    for thread in threads:
                        thread.start()
                    for thread in threads:
                        thread.join()
                except Exception:
                    traceback.print_exc()
        logger.info('SSDPDiscover.search()')

    def _search(self, host, ssdp_ttl, ssdp_mx, ssdp_amount):
        logger.debug('Binding socket to "{}" ...'.format(host or ''))
        sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.settimeout(ssdp_mx)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_MULTICAST_TTL,
            ssdp_ttl)
        sock.bind((host, self.MSEARCH_PORT))

        for i in range(1, ssdp_amount + 1):
            t = threading.Timer(
                float(i) / 2, self._send_discover, args=[sock, ssdp_mx])
            t.start()

        while True:
            try:
                header, address = sock.recvfrom(self.BUFFER_SIZE)
                if self.cb_on_device_response:
                    guess = chardet.detect(header)
                    header = header.decode(guess['encoding'])
                    header = pulseaudio_dlna.plugins.dlna.ssdp._get_header_map(
                        header)
                    self.cb_on_device_response(header, address)
            except socket.timeout:
                break
        sock.close()

    def _send_discover(self, sock, ssdp_mx):
        msg = self.MSEARCH_MSG.format(
            host=self.SSDP_ADDRESS, port=self.SSDP_PORT, mx=ssdp_mx).encode()
        if self.USE_SINGLE_SOCKET:
            for addr in self.addresses:
                sock.setsockopt(
                    socket.SOL_IP, socket.IP_MULTICAST_IF,
                    socket.inet_aton(addr))
                sock.sendto(msg, (self.SSDP_ADDRESS, self.SSDP_PORT))
        else:
            sock.sendto(msg, (self.SSDP_ADDRESS, self.SSDP_PORT))
