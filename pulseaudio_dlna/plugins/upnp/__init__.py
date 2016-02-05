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

import pulseaudio_dlna.plugins
import pulseaudio_dlna.plugins.upnp.renderer


class DLNAPlugin(pulseaudio_dlna.plugins.BasePlugin):
    def __init__(self, *args):
        pulseaudio_dlna.plugins.BasePlugin.__init__(self, *args)
        self.st_headers = [
            'urn:schemas-upnp-org:device:MediaRenderer:1',
            'urn:schemas-upnp-org:device:MediaRenderer:2',
        ]

    def lookup(self, locations):
        renderers = []
        for url in locations:
            renderer = pulseaudio_dlna.plugins.upnp.renderer.UpnpMediaRendererFactory.from_url(
                url, pulseaudio_dlna.plugins.upnp.renderer.CoinedUpnpMediaRenderer)
            if renderer is not None:
                renderers.append(renderer)
        return renderers

    def create_device(self, header):
        return pulseaudio_dlna.plugins.upnp.renderer.UpnpMediaRendererFactory.from_header(
            header,
            pulseaudio_dlna.plugins.upnp.renderer.CoinedUpnpMediaRenderer)
