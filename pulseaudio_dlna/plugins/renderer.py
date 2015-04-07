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
import random
import urlparse
import functools

import pulseaudio_dlna.common
import pulseaudio_dlna.pulseaudio


@functools.total_ordering
class BaseRenderer(object):

    IDLE = 'idle'
    PLAYING = 'playing'
    PAUSE = 'paused'
    STOP = 'stopped'

    def __init__(self):
        self._name = None
        self._short_name = None
        self._label = None
        self._ip = None
        self._port = None
        self._state = None
        self._encoder = None
        self._flavour = None
        self._protocols = []

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        name = name.strip()
        if name == '':
            name = 'Unnamed device #{random_id}'.format(
                random_id=random.randint(1000, 9999))
        self._short_name = '{filtered_name}_{flavour}'.format(
            filtered_name=re.sub(r'[^a-z0-9]', '', name.lower()),
            flavour=self.flavour.lower())
        self._name = name

    @property
    def short_name(self):
        return self._short_name

    @property
    def label(self):
        return '{name} ({flavour})'.format(
            name=self.name, flavour=self.flavour)

    @property
    def ip(self):
        return self._ip

    @ip.setter
    def ip(self, value):
        self._ip = value

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        self._port = value

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value):
        self._state = value

    @property
    def encoder(self):
        if self._encoder is None:
            for encoder in pulseaudio_dlna.common.supported_encoders:
                for mime_type in encoder.mime_types:
                    if mime_type in self.protocols:
                        return encoder
        else:
            return self._encoder

    @encoder.setter
    def encoder(self, value):
        self._encoder = value

    @property
    def flavour(self):
        return self._flavour

    @flavour.setter
    def flavour(self, value):
        self._flavour = value

    @property
    def protocols(self):
        return self._protocols

    @protocols.setter
    def protocols(self, value):
        self._protocols = value

    def activate(self):
        pass

    def play(self):
        raise NotImplementedError()

    def pause(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

    def __eq__(self, other):
        if isinstance(other, BaseRenderer):
            return self.short_name == other.short_name
        if isinstance(other, pulseaudio_dlna.pulseaudio.PulseBridge):
            return self.short_name == other.device.short_name

    def __gt__(self, other):
        if isinstance(other, BaseRenderer):
            return self.short_name > other.short_name
        if isinstance(other, pulseaudio_dlna.pulseaudio.PulseBridge):
            return self.short_name > other.device.short_name

    def __str__(self):
        return '<{} name="{}" short="{}" state="{}" protocols="{}">'.format(
            self.__class__.__name__,
            self.name,
            self.short_name,
            self.state,
            ','.join(self.protocols),
        )


class CoinedBaseRendererMixin():

    server_ip = None
    server_port = None

    def set_server_location(self, ip, port):
        self.server_ip = ip
        self.server_port = port

    def get_stream_url(self):
        server_url = 'http://{ip}:{port}'.format(
            ip=self.server_ip,
            port=self.server_port,
        )
        stream_name = '/{stream_name}.{suffix}'.format(
            stream_name=self.short_name,
            suffix=self.encoder.suffix,
        )
        return urlparse.urljoin(server_url, stream_name)

    def play(self):
        raise NotImplementedError()
