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

import netifaces
import traceback
import socket
import logging

logger = logging.getLogger('pulseaudio_dlna.utils.network')

LOOPBACK_IP = '127.0.0.1'


def default_ipv4():
    try:
        default_if = netifaces.gateways()['default'][netifaces.AF_INET][1]
        return netifaces.ifaddresses(default_if)[netifaces.AF_INET][0]['addr']
    except Exception:
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
    try:
        return __pyroute2_get_host_by_ip(ip)
    except ImportError:
        logger.warning(
            'Could not import module "pyroute2". '
            'Falling back to module "netaddr"!')
    try:
        return __netaddr_get_host_by_ip(ip)
    except ImportError:
        logger.critical(
            'Could not import module "netaddr". '
            'Either "pyroute2" or "netaddr" must be available for automatic '
            'interface detection! You can manually select the appropriate '
            'host yourself via the --host option.')
    return None


def __pyroute2_get_host_by_ip(ip):
    import pyroute2
    ipr = pyroute2.IPRoute()
    routes = ipr.get_routes(family=socket.AF_INET, dst=ip)
    ipr.close()
    for route in routes:
        for attr in route.get('attrs', []):
            if type(attr) is list:
                if attr[0] == 'RTA_PREFSRC':
                    return attr[1]
            else:
                if attr.cell[0] == 'RTA_PREFSRC':
                    return attr.get_value()
    logger.critical(
        '__pyroute2_get_host_by_ip() - No host found for IP {}!'.format(ip))
    return None


def __netaddr_get_host_by_ip(ip):
    import netaddr
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
    logger.critical(
        '__netaddr_get_host_by_ip - No host found for IP {}!'.format(ip))
    return None
