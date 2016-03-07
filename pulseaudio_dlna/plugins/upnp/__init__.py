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

import logging
import threading
import traceback

import pulseaudio_dlna.plugins
import pulseaudio_dlna.plugins.upnp.ssdp
import pulseaudio_dlna.plugins.upnp.ssdp.listener
import pulseaudio_dlna.plugins.upnp.ssdp.discover
from pulseaudio_dlna.plugins.upnp.renderer import (
    CoinedUpnpMediaRenderer, UpnpMediaRendererFactory)

logger = logging.getLogger('pulseaudio_dlna.plugins.upnp')


class DLNAPlugin(pulseaudio_dlna.plugins.BasePlugin):

    NOTIFICATION_TYPES = [
        'urn:schemas-upnp-org:device:MediaRenderer:1',
        'urn:schemas-upnp-org:device:MediaRenderer:2',
    ]

    def __init__(self, *args):
        pulseaudio_dlna.plugins.BasePlugin.__init__(self, *args)

    def lookup(self, url, xml):
        return UpnpMediaRendererFactory.from_xml(
            url, xml, CoinedUpnpMediaRenderer)

    def discover(self, holder, ttl=None):
        self.holder = holder

        def launch_discover():
            discover = pulseaudio_dlna.plugins.upnp.ssdp.discover\
                .SSDPDiscover(
                    cb_on_device_response=self._on_device_response,
                )
            discover.search(ssdp_ttl=ttl)

        def launch_listener():
            ssdp = pulseaudio_dlna.plugins.upnp.ssdp.listener\
                .ThreadedSSDPListener(
                    cb_on_device_alive=self._on_device_added,
                    cb_on_device_byebye=self._on_device_removed
                )
            ssdp.run(ttl=ttl)

        threads = []
        for func in [launch_discover, launch_listener]:
            thread = threading.Thread(target=func)
            thread.daemon = True
            threads.append(thread)
        try:
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join()
        except:
            traceback.print_exc()

        logger.debug('DLNAPlugin.discover() quit')

    @pulseaudio_dlna.plugins.BasePlugin.add_device_after
    def _on_device_response(self, header, address):
        st_header = header.get('st', None)
        if st_header and st_header in self.NOTIFICATION_TYPES:
            return UpnpMediaRendererFactory.from_header(
                header, CoinedUpnpMediaRenderer)

    @pulseaudio_dlna.plugins.BasePlugin.add_device_after
    def _on_device_added(self, header):
        nt_header = header.get('nt', None)
        if nt_header and nt_header in self.NOTIFICATION_TYPES:
            return UpnpMediaRendererFactory.from_header(
                header, CoinedUpnpMediaRenderer)

    @pulseaudio_dlna.plugins.BasePlugin.remove_device_after
    def _on_device_removed(self, header):
        nt_header = header.get('nt', None)
        if nt_header and nt_header in self.NOTIFICATION_TYPES:
            device_id = pulseaudio_dlna.plugins.upnp.ssdp._get_device_id(
                header)
            return device_id
