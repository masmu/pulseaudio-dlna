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
import zeroconf
import gobject
import time

logger = logging.getLogger('pulseaudio_dlna.listeners.mdns')


class GoogleCastGroupHandler(object):

    UDN_PREFIX = 'gcg'
    GOOGLE_CAST_GROUP = 'Google Cast Group'

    def __init__(self, holder):
        self.holder = holder

    def remove_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        device_info = self._get_device_info(info)
        logger.info('removed {}'.format(device_info))

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        device_info = self._get_device_info(info)
        logger.info('added {}'.format(device_info))
        if device_info and device_info['type'] == self.GOOGLE_CAST_GROUP:
            self.holder.process_cast_group(device_info)

    def _get_device_info(self, info):
        try:
            return {
                'udn': '{}:{}'.format(self.UDN_PREFIX, info.properties['id']),
                'type': info.properties['md'].decode('utf-8'),
                'name': info.properties['fn'].decode('utf-8'),
                'ip': self._bytes2string(info.address),
                'port': int(info.port),
            }
        except (KeyError, AttributeError):
            pass

    def _bytes2string(self, bytes):
        ip = []
        for b in bytes:
            subnet = int(b.encode('hex'), 16)
            ip.append(str(subnet))
        return '.'.join(ip)


class MDNSListener(object):

    SERVICE_TYPE = '_googlecast._tcp.local.'

    def __init__(self, holder):
        self.holder = holder
        self.zeroconf = None
        self.mainloop = None

    def run(self):
        self.zeroconf = zeroconf.Zeroconf()
        handler = GoogleCastGroupHandler(self.holder)
        zeroconf.ServiceBrowser(
            self.zeroconf, self.SERVICE_TYPE, handler)

        self.mainloop = gobject.MainLoop()
        context = self.mainloop.get_context()
        while True:
            try:
                if context.pending():
                    context.iteration(True)
                else:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                break
        self.shutdown()

    def shutdown(self):
        self.zeroconf.close()
