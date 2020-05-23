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


import logging

import pulseaudio_dlna.plugins
import pulseaudio_dlna.plugins.chromecast.mdns
from pulseaudio_dlna.plugins.chromecast.renderer import ChromecastRendererFactory

logger = logging.getLogger('pulseaudio_dlna.plugins.chromecast')


class ChromecastPlugin(pulseaudio_dlna.plugins.BasePlugin):

    GOOGLE_MDNS_DOMAIN = '_googlecast._tcp.local.'

    def __init__(self, *args):
        pulseaudio_dlna.plugins.BasePlugin.__init__(self, *args)

    def lookup(self, url, xml):
        return ChromecastRendererFactory.from_xml(url, xml)

    def discover(self, holder, ttl=None, host=None):
        self.holder = holder
        mdns = pulseaudio_dlna.plugins.chromecast.mdns.MDNSListener(
            domain=self.GOOGLE_MDNS_DOMAIN,
            host=host,
            cb_on_device_added=self._on_device_added,
            cb_on_device_removed=self._on_device_removed
        )
        mdns.run(ttl)

    @pulseaudio_dlna.plugins.BasePlugin.add_device_after
    def _on_device_added(self, mdns_info):
        if mdns_info:
            return ChromecastRendererFactory.from_mdns_info(mdns_info)
        return None

    @pulseaudio_dlna.plugins.BasePlugin.remove_device_after
    def _on_device_removed(self, mdns_info):
        return None
