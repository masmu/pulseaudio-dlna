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

import re
import logging

logger = logging.getLogger('pulseaudio_dlna.renderers')


class RendererHolder(object):
    def __init__(self, stream_server, message_queue,plugins, device_filter=None):
        self.renderers = {}
        self.registered = {}
        self.stream_server = stream_server
        self.device_filter = device_filter
        self.message_queue = message_queue
        for plugin in plugins:
            self._register(plugin.st_header, plugin)

    def add_renderers_by_url(self, locations):
        # TODO implement me
        pass

    def _register(self, identifier, _type):
        self.registered[identifier] = _type

    def _retrieve_header_map(self, header):
        header = re.findall(r"(?P<name>.*?): (?P<value>.*?)\r\n", header)
        header = {k.lower(): v for k, v in dict(header).items()}
        return header

    def _retrieve_device_id(self, header):
        if 'usn' in header:
            match = re.search("uuid:([0-9a-f\-]+)::.*", header['usn'], re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _add_renderer_with_filter_check(self, device_id, device):
        if self.device_filter is None or device.name in self.device_filter:
            self._add_renderer(device_id, device)
        else:
            logger.info('Skipped the device "{name}."'.format(
                name=device.name))

    def _add_renderer(self, device_id, device):
        device.activate()
        device.set_server_location(self.stream_server.ip, self.stream_server.port)
        self.renderers[device_id] = device
        self.message_queue.put({
            'type': 'add_device',
            'device': device
        })

    def _remove_renderer_by_id(self, device_id):
        device = self.renderers[device_id]
        self.message_queue.put({
            'type': 'remove_device',
            'device': device
        })
        del self.renderers[device_id]

    def add_from_search(self, header):
        header = self._retrieve_header_map(header)
        device_id = self._retrieve_device_id(header)

        if device_id is not None and device_id not in self.renderers:
            if 'st' in header:
                st_header = header['st']
                if st_header in self.registered:
                    device = self.registered[st_header].create_device(header)
                    if device is not None:
                        self._add_renderer_with_filter_check(device_id, device)

    def process_notify_request(self, header):
        header = self._retrieve_header_map(header)
        device_id = self._retrieve_device_id(header)

        if device_id is not None:
            if 'nts' in header:
                nts_header = header['nts']
                if nts_header == 'ssdp:alive' and device_id not in self.renderers and 'nt' in header:
                    nt_header = header['nt']
                    if nt_header in self.registered:
                        device = self.registered[nt_header].create_device(header)
                        if device is not None:
                            self._add_renderer_with_filter_check(device_id, device)
                elif nts_header == 'ssdp:byebye' and device_id in self.renderers:
                    nt_header = header['nt']
                    if nt_header in self.registered:
                        self._remove_renderer_by_id(device_id)