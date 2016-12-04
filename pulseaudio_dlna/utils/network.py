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
import traceback


def default_ipv4():
    try:
        default_if = netifaces.gateways()['default'][netifaces.AF_INET][1]
        return netifaces.ifaddresses(default_if)[netifaces.AF_INET][0]['addr']
    except:
        traceback.print_exc()
    return None


def ipv4_addresses():
    ips = []
    for iface in netifaces.interfaces():
        for link in netifaces.ifaddresses(iface).get(netifaces.AF_INET, []):
            ip = link.get('addr', None)
            if ip:
                ips.append(ip)
    return ips
