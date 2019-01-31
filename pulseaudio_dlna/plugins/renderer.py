#!/usr/bin/python3

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
import random
import urllib.parse
import functools
import logging
import base64

import pulseaudio_dlna.pulseaudio
import pulseaudio_dlna.rules
import pulseaudio_dlna.streamserver
import pulseaudio_dlna.utils.network

logger = logging.getLogger('pulseaudio_dlna.plugins.renderer')

DISABLE_MIMETYPE_CHECK = False


class NoEncoderFoundException(Exception):
    def __init__(self):
        Exception.__init__(
            self,
            'Could not find a suitable encoder!'
        )


class NoSuitableHostFoundException(Exception):
    def __init__(self, address):
        Exception.__init__(
            self,
            'Could not find a suitable host address for "{}"!'.format(address)
        )


@functools.total_ordering
class BaseRenderer(object):

    STATE_PLAYING = 'PLAYING'
    STATE_PAUSED = 'PAUSED'
    STATE_STOPPED = 'STOPPED'

    REQUEST_TIMEOUT = 10

    def __init__(self, udn, flavour, name=None, ip=None, port=None,
                 model_name=None, model_number=None,
                 model_description=None, manufacturer=None):
        self._udn = None
        self._name = None
        self._ip = None
        self._port = None
        self._model_name = None
        self._model_number = None
        self._model_description = None
        self._manufacturer = None

        self._short_name = None
        self._label = None
        self._state = self.STATE_STOPPED
        self._encoder = None
        self._flavour = None
        self._codecs = []
        self._rules = pulseaudio_dlna.rules.Rules()
        self._workarounds = []

        self.udn = udn
        self.flavour = flavour
        self.name = name
        self.ip = ip
        self.port = port
        self.model_name = model_name
        self.model_number = model_number
        self.model_description = model_description
        self.manufacturer = manufacturer

    @property
    def udn(self):
        return self._udn

    @udn.setter
    def udn(self, value):
        self._udn = value

    @property
    def model_name(self):
        return self._model_name

    @model_name.setter
    def model_name(self, value):
        self._model_name = value

    @property
    def model_number(self):
        return self._model_number

    @model_number.setter
    def model_number(self, value):
        self._model_number = value

    @property
    def model_description(self):
        return self._model_description

    @model_description.setter
    def model_description(self, value):
        self._model_description = value

    @property
    def manufacturer(self):
        return self._manufacturer

    @manufacturer.setter
    def manufacturer(self, value):
        self._manufacturer = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        if not name:
            name = ''
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
    def codec(self):
        for codec in self.codecs:
            if codec.enabled and codec.encoder and codec.encoder.available:
                return codec

        missing_encoders = []
        for codec in self.codecs:
            for identifier, encoder_type in list(codec.ENCODERS.items()):
                encoder = encoder_type()
                if encoder.binary not in missing_encoders:
                    missing_encoders.append(encoder.binary)

        logger.info(
            'There was no suitable codec found for "{name}". '
            'The device can play "{codecs}". Install one of following '
            'encoders: "{encoders}". '.format(
                name=self.label,
                codecs=','.join(
                    [codec.mime_type for codec in self.codecs]),
                encoders=','.join(missing_encoders),
            ) +
            'You can also try to disable the mime type check with the '
            '"--disable-mimetype-check" flag. But be warned: In that way you '
            'can use codecs your device does not support officially and this '
            'could lead to distortions or in rare cases to speaker damage!')
        raise NoEncoderFoundException()

    @property
    def flavour(self):
        return self._flavour

    @flavour.setter
    def flavour(self, value):
        self._flavour = value

    @property
    def codecs(self):
        return self._codecs

    @codecs.setter
    def codecs(self, value):
        self._codecs = value

    @property
    def rules(self):
        return self._rules

    @rules.setter
    def rules(self, value):
        self._rules = value

    @property
    def workarounds(self):
        return self._workarounds

    @workarounds.setter
    def workarounds(self, value):
        self._workarounds = value

    def activate(self):
        pass

    def validate(self):
        return True

    def play(self):
        raise NotImplementedError()

    def pause(self):
        raise NotImplementedError()

    def stop(self):
        raise NotImplementedError()

    def add_mime_type(self, mime_type):
        for identifier, _type in pulseaudio_dlna.codecs.CODECS.items():
            if _type.accepts(mime_type):
                codec = _type(mime_type)
                if codec not in self.codecs:
                    self.codecs.append(codec)

    def prioritize_codecs(self):

        def sorting_algorithm(codec):
            if isinstance(codec, pulseaudio_dlna.codecs.L16Codec):
                value = codec.priority * 100000
                if codec.sample_rate:
                    value += 200 - abs((44100 - codec.sample_rate) / 1000)
                if codec.channels:
                    value *= codec.channels
                return value
            else:
                return codec.priority * 100000

        self.codecs.sort(key=sorting_algorithm, reverse=True)

    def apply_device_rules(self):
        for rule in self.rules:
            if type(rule) is pulseaudio_dlna.rules.REQUEST_TIMEOUT:
                self.REQUEST_TIMEOUT = rule.timeout

        if (pulseaudio_dlna.plugins.renderer.DISABLE_MIMETYPE_CHECK or
           pulseaudio_dlna.rules.DISABLE_MIMETYPE_CHECK in self.rules):
            for codec in pulseaudio_dlna.codecs.enabled_codecs():
                if codec not in self.codecs:
                    self.codecs.append(codec)

    def apply_device_fixes(self):
        if self.manufacturer == 'Sonos, Inc.':
            for codec in self.codecs:
                if type(codec) in [
                        pulseaudio_dlna.codecs.Mp3Codec,
                        pulseaudio_dlna.codecs.OggCodec]:
                    codec.rules.append(
                        pulseaudio_dlna.rules.FAKE_HTTP_CONTENT_LENGTH())

        if self.manufacturer == 'Raumfeld GmbH':
            if (self.model_description == 'Virtual Media Player' and
               pulseaudio_dlna.rules.DISABLE_MIMETYPE_CHECK not in self.rules):
                self.rules.append(
                    pulseaudio_dlna.rules.DISABLE_MIMETYPE_CHECK())

    def set_rules_from_config(self, config):
        self.name = config['name']
        for rule in config.get('rules', []):
            self.rules.append(rule)
        for codec_properties in config.get('codecs', []):
            codec_type = pulseaudio_dlna.codecs.CODECS[
                codec_properties['identifier']]
            codec = codec_type(codec_properties['mime_type'])
            for k, v in codec_properties.items():
                forbidden_attributes = ['mime_type', 'identifier', 'rules']
                if hasattr(codec, k) and k not in forbidden_attributes:
                    setattr(codec, k, v)
            for rule in codec_properties.get('rules', []):
                codec.rules.append(rule)
            self.codecs.append(codec)
        self.apply_device_rules()
        logger.debug(
            'Loaded the following device configuration:\n{}'.format(
                self.__str__(True)))
        return True

    def _encode_settings(self, settings, suffix=''):
        if pulseaudio_dlna.streamserver.StreamServer.HOST:
            server_ip = pulseaudio_dlna.streamserver.StreamServer.HOST
        else:
            server_ip = pulseaudio_dlna.utils.network.get_host_by_ip(self.ip)
        if not server_ip:
            raise NoSuitableHostFoundException(self.ip)
        server_port = pulseaudio_dlna.streamserver.StreamServer.PORT
        base_url = 'http://{ip}:{port}'.format(
            ip=server_ip,
            port=server_port,
        )
        data_string = ','.join(
            ['{}="{}"'.format(k, v) for k, v in settings.items()])
        stream_name = '/{base_string}/{suffix}'.format(
            base_string=urllib.parse.quote(base64.b64encode(data_string.encode())),
            suffix=suffix,
        )
        return urllib.parse.urljoin(base_url, stream_name)

    def get_stream_url(self):
        settings = {
            'type': 'bridge',
            'udn': self.udn,
        }
        return self._encode_settings(settings, 'stream.' + self.codec.suffix)

    def get_image_url(self, name='default.png'):
        settings = {
            'type': 'image',
            'name': name,
        }
        return self._encode_settings(settings)

    def get_sys_icon_url(self, name):
        settings = {
            'type': 'sys-icon',
            'name': name,
        }
        return self._encode_settings(settings)

    def _before_register(self):
        for workaround in self.workarounds:
            workaround.run('before_register')

    def _after_register(self):
        for workaround in self.workarounds:
            workaround.run('after_register')

    def _before_play(self):
        for workaround in self.workarounds:
            workaround.run('before_play')

    def _after_play(self):
        for workaround in self.workarounds:
            workaround.run('after_play')

    def _before_stop(self):
        for workaround in self.workarounds:
            workaround.run('before_stop')

    def _after_stop(self):
        for workaround in self.workarounds:
            workaround.run('after_stop')

    def __eq__(self, other):
        if isinstance(other, BaseRenderer):
            return self.udn == other.udn
        if isinstance(other, pulseaudio_dlna.pulseaudio.PulseBridge):
            return self.udn == other.device.udn

    def __gt__(self, other):
        if isinstance(other, BaseRenderer):
            return self.udn > other.udn
        if isinstance(other, pulseaudio_dlna.pulseaudio.PulseBridge):
            return self.udn > other.device.udn

    def __str__(self, detailed=False):
        return (
            '<{} name="{}" short="{}" state="{}" udn="{}" model_name="{}" '
            'model_number="{}" model_description="{}" manufacturer="{}" '
            'timeout="{}">{}{}').format(
                self.__class__.__name__,
                self.name,
                self.short_name,
                self.state,
                self.udn,
                self.model_name,
                self.model_number,
                self.model_description,
                self.manufacturer,
                self.REQUEST_TIMEOUT,
                ('\n' if len(self.rules) > 0 else '') + '\n'.join(
                    ['  - ' + str(rule) for rule in self.rules]
                ) if detailed else '',
                '\n' + '\n'.join([
                    '  ' + codec.__str__(detailed) for codec in self.codecs
                ]) if detailed else '',
        )

    def to_json(self):
        return {
            'name': self.name,
            'flavour': self.flavour,
            'codecs': self.codecs,
            'rules': self.rules,
        }
