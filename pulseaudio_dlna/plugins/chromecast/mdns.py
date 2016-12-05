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

from gi.repository import GObject

import logging
import zeroconf
import time

logger = logging.getLogger('pulseaudio_dlna.plugins.chromecast.mdns')


class MDNSHandler(object):

    def __init__(self, server):
        self.server = server

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if self.server.cb_on_device_added:
            self.server.cb_on_device_added(info)

    def remove_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        if self.server.cb_on_device_removed:
            self.server.cb_on_device_removed(info)


class MDNSListener(object):

    def __init__(
            self, domain,
            host=None,
            cb_on_device_added=None, cb_on_device_removed=None):
        self.domain = domain
        self.host = host
        self.cb_on_device_added = cb_on_device_added
        self.cb_on_device_removed = cb_on_device_removed

    def run(self, ttl=None):
        if self.host:
            self.zeroconf = zeroconf.Zeroconf(interfaces=[self.host])
        else:
            self.zeroconf = zeroconf.Zeroconf()
        zeroconf.ServiceBrowser(self.zeroconf, self.domain, MDNSHandler(self))

        if ttl:
            GObject.timeout_add(ttl * 1000, self.shutdown)

        self.__running = True
        self.__mainloop = GObject.MainLoop()
        context = self.__mainloop.get_context()
        while self.__running:
            try:
                if context.pending():
                    context.iteration(True)
                else:
                    time.sleep(0.01)
            except KeyboardInterrupt:
                break
        self.zeroconf.close()
        logger.debug('MDNSListener.run() quit')

    def shutdown(self):
        logger.debug('MDNSListener.shutdown()')
        self.__running = False
