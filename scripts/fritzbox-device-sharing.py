#!/usr/bin/python3
# -*- coding: utf-8 -*-

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



import requests
import sys
import json

import pulseaudio_dlna
import pulseaudio_dlna.holder
import pulseaudio_dlna.plugins.dlna
import pulseaudio_dlna.codecs


STEPS_PATTERN = """
    Step 1: Open your Fritzbox web interface (http://fritz.box/)
    Step 2: Goto Internet -> Permit Access -> Port-Sharing
    Step 3: Add a port sharing via the button "New Port Sharing" for each device you want to share.
"""

SHARE_PATTERN = """#############################################################################

    To share access to the device "{name}" add the following entry:

    -------------------------------------------------------

       Create New Port Sharing

       [x] Port sharing enabled for "Other applications"')
          Name:          "DLNA for {name}" (does not matter, just the name of the rule)
          Protocol:      "TCP"
          From Port      "{port}"    To Port: "{port}"
          To Computer:   "?" (does not matter, make sure the IP address is correct)
          To IP-Address: "{ip}"
          To Port:       "{port}"

                                                       [OK]

    -------------------------------------------------------

    The link to share the device is : {link}
"""


class IPDetector():

    TIMEOUT = 5

    def __init__(self):
        self.public_ip = None

    def get_public_ip(self):
        self.public_ip = self._get_public_ip()
        return self.public_ip is not None

    def _get_public_ip(self):
        response = requests.get('http://ifconfig.lancode.de')
        if response.status_code == 200:
            data = json.loads(response.content)
            return data.get('ip', None)
        return None


class DLNADiscover():

    PLUGINS = [
        pulseaudio_dlna.plugins.dlna.DLNAPlugin(),
    ]
    TIMEOUT = 5

    def __init__(self, max_workers=10):
        self.devices = []

    def discover_devices(self):
        self.devices = self._discover_devices()
        return len(self.devices) > 0

    def _discover_devices(self):
        holder = pulseaudio_dlna.holder.Holder(self.PLUGINS)
        holder.search(ttl=self.TIMEOUT)
        return list(holder.devices.values())


ip_detector = IPDetector()
print('Getting your external IP address ...')
if not ip_detector.get_public_ip():
    print('Could not get your external IP! Aborting.')
    sys.exit(1)

print('Discovering devices ...')
dlna_discover = DLNADiscover()
if not dlna_discover.discover_devices():
    print('Could not find any devices! Aborting.')
    sys.exit(1)

print(STEPS_PATTERN)
for device in dlna_discover.devices:
    link = device.upnp_device.access_url.replace(
        device.ip, ip_detector.public_ip)
    print((SHARE_PATTERN.format(
        name=device.name, ip=device.ip, port=device.port, link=link)))
