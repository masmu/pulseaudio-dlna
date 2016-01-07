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

import re
import logging
import threading

logger = logging.getLogger('pulseaudio_dlna.renderers')


class RendererHolder(object):

    SSDP_ALIVE = 'ssdp:alive'
    SSDP_BYEBYE = 'ssdp:byebye'

    def __init__(
            self, plugins,
            stream_ip=None, stream_port=None, message_queue=None,
            device_filter=None, device_config=None):
        self.renderers = {}
        self.registered = {}
        self.stream_ip = stream_ip
        self.stream_port = stream_port
        self.device_filter = device_filter
        self.device_config = device_config or {}
        self.message_queue = message_queue
        self.lock = threading.Lock()
        for plugin in plugins:
            for st_header in plugin.st_headers:
                self.registered[st_header] = plugin

    def _retrieve_header_map(self, header):
        header = re.findall(r"(?P<name>.*?): (?P<value>.*?)\n", header)
        header = {k.lower(): v.strip() for k, v in dict(header).items()}
        return header

    def _retrieve_device_id(self, header):
        if 'usn' in header:
            match = re.search(
                "(uuid:.*?)::(.*)", header['usn'], re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def process_locations(self, locations):
        try:
            self.lock.acquire()
            for plugin in self.registered.values():
                for device in plugin.lookup(locations):
                    self._add_renderer(device.udn, device)
        finally:
            self.lock.release()

    def process_msearch_request(self, header):
        header = self._retrieve_header_map(header)
        device_id = self._retrieve_device_id(header)

        if device_id is None:
            return
        try:
            self.lock.acquire()
            st_header = header.get('st', None)
            if st_header and st_header in self.registered:
                if device_id not in self.renderers:
                    device = self.registered[st_header].create_device(header)
                    if device is not None:
                        self._add_renderer_with_filter_check(device_id, device)
        finally:
            self.lock.release()

    def process_notify_request(self, header):
        header = self._retrieve_header_map(header)
        device_id = self._retrieve_device_id(header)

        if device_id is None:
            return
        try:
            self.lock.acquire()
            nts_header = header.get('nts', None)
            nt_header = header.get('nt', None)
            if nt_header and nts_header and nt_header in self.registered:
                if (nts_header == self.SSDP_ALIVE and
                        device_id not in self.renderers):
                    plugin = self.registered[nt_header]
                    device = plugin.create_device(header)
                    if device is not None:
                        self._add_renderer_with_filter_check(device_id, device)
                elif (nts_header == self.SSDP_BYEBYE and
                        device_id in self.renderers):
                    self._remove_renderer_by_id(device_id)
        finally:
            self.lock.release()

    def _add_renderer_with_filter_check(self, device_id, device):
        if self.device_filter is None or device.name in self.device_filter:
            self._add_renderer(device_id, device)
        else:
            logger.info('Skipped the device "{name}" ...'.format(
                name=device.label))

    def _add_renderer(self, device_id, device):
        if device.validate():
            config = self.device_config.get(device.udn, None)
            device.activate(config)
            if config:
                logger.info(
                    'Using device configuration:\n' + device.__str__(True))
            if self.stream_ip and self.stream_port:
                device.set_server_location(self.stream_ip, self.stream_port)
            self.renderers[device_id] = device
            if self.message_queue:
                self.message_queue.put({
                    'type': 'add_device',
                    'device': device
                })

    def _remove_renderer_by_id(self, device_id):
        device = self.renderers[device_id]
        if self.message_queue:
            self.message_queue.put({
                'type': 'remove_device',
                'device': device
            })
        del self.renderers[device_id]
