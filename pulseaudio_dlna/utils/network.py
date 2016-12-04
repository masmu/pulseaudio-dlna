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

import netifaces
import netaddr
import traceback
import logging

logger = logging.getLogger('pulseaudio_dlna.utils.network')

LOOPBACK_IP = '127.0.0.1'


def default_ipv4():
    try:
        default_if = netifaces.gateways()['default'][netifaces.AF_INET][1]
        return netifaces.ifaddresses(default_if)[netifaces.AF_INET][0]['addr']
    except:
        traceback.print_exc()
    return None


def ipv4_addresses(include_loopback=False):
    ips = []
    for iface in netifaces.interfaces():
        for link in netifaces.ifaddresses(iface).get(netifaces.AF_INET, []):
            ip = link.get('addr', None)
            if ip:
                if ip != LOOPBACK_IP or include_loopback is True:
                    ips.append(ip)
    return ips


def get_host_by_ip(ip):
    host = netaddr.IPAddress(ip)
    for iface in netifaces.interfaces():
        for link in netifaces.ifaddresses(iface).get(netifaces.AF_INET, []):
            addr = link.get('addr', None)
            netmask = link.get('netmask', None)
            if addr and netmask:
                if host in netaddr.IPNetwork('{}/{}'.format(addr, netmask)):
                    logger.debug(
                        'Selecting host "{}" for IP "{}"'.format(addr, ip))
                    return addr
    logger.critical('No host found for IP {}!'.format(ip))
    return None
