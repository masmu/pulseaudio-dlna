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

import functools
import logging
import re
import inspect
import sys

import pulseaudio_dlna.encoders
import pulseaudio_dlna.rules

logger = logging.getLogger('pulseaudio_dlna.codecs')

BACKENDS = ['generic', 'ffmpeg', 'avconv', 'pulseaudio']
CODECS = {}


class UnknownBackendException(Exception):
    def __init__(self, backend):
        Exception.__init__(
            self,
            'You specified an unknown backend "{}"!'.format(backend)
        )


class UnknownCodecException(Exception):
    def __init__(self, codec):
        Exception.__init__(
            self,
            'You specified an unknown codec "{}"!'.format(codec),
        )


class UnsupportedCodecException(Exception):
    def __init__(self, codec, backend):
        Exception.__init__(
            self,
            'You specified an unsupported codec "{}" for the '
            'backend "{}"!'.format(codec, backend),
        )


def set_backend(backend):
    if backend in BACKENDS:
        BaseCodec.BACKEND = backend
        return
    raise UnknownBackendException(backend)


def set_codecs(identifiers):
    step = 3
    priority = (len(CODECS) + 1) * step
    for identifier, _type in CODECS.items():
        _type.ENABLED = False
        _type.PRIORITY = 0
    for identifier in identifiers:
        try:
            CODECS[identifier].ENABLED = True
            CODECS[identifier].PRIORITY = priority
            priority = priority - step
        except KeyError:
            raise UnknownCodecException(identifier)


def enabled_codecs():
    codecs = []
    for identifier, _type in CODECS.items():
        if _type.ENABLED:
            codecs.append(_type())
    return codecs


@functools.total_ordering
class BaseCodec(object):

    ENABLED = True
    IDENTIFIER = None
    BACKEND = 'generic'
    PRIORITY = None

    def __init__(self):
        self.mime_type = None
        self.suffix = None
        self.rules = pulseaudio_dlna.rules.Rules()

    @property
    def enabled(self):
        return type(self).ENABLED

    @enabled.setter
    def enabled(self, value):
        type(self).ENABLED = value

    @property
    def priority(self):
        return type(self).PRIORITY

    @priority.setter
    def priority(self, value):
        type(self).PRIORITY = value

    @property
    def specific_mime_type(self):
        return self.mime_type

    @property
    def encoder(self):
        return self.encoder_type()

    @property
    def encoder_type(self):
        if self.BACKEND in self.ENCODERS:
            return self.ENCODERS[self.BACKEND]
        else:
            raise UnsupportedCodecException(self.IDENTIFIER, self.BACKEND)

    @classmethod
    def accepts(cls, mime_type):
        for accepted_mime_type in cls.SUPPORTED_MIME_TYPES:
            if mime_type.lower().startswith(accepted_mime_type.lower()):
                return True
        return False

    def get_recorder(self, monitor):
        if self.BACKEND == 'pulseaudio':
            return pulseaudio_dlna.recorders.PulseaudioRecorder(
                monitor, codec=self)
        else:
            return pulseaudio_dlna.recorders.PulseaudioRecorder(monitor)

    def __eq__(self, other):
        return type(self) is type(other)

    def __gt__(self, other):
        return type(self) is type(other)

    def __str__(self, detailed=False):
        return '<{} enabled="{}" priority="{}" mime_type="{}" ' \
               'backend="{}">{}{}'.format(
                   self.__class__.__name__,
                   self.enabled,
                   self.priority,
                   self.specific_mime_type,
                   self.BACKEND,
                   ('\n' if len(self.rules) > 0 else '') + '\n'.join(
                       ['    - ' + str(rule) for rule in self.rules]
                   ) if detailed else '',
                   '\n    ' + str(self.encoder) if detailed else '',
               )

    def to_json(self):
        attributes = ['priority', 'suffix', 'mime_type']
        d = {
            k: v for k, v in iter(self.__dict__.items())
            if k not in attributes
        }
        d['mime_type'] = self.specific_mime_type
        d['identifier'] = self.IDENTIFIER
        return d


class BitRateMixin(object):

    def __init__(self):
        self.bit_rate = None

    @property
    def encoder(self):
        return self.encoder_type(self.bit_rate)

    def __eq__(self, other):
        return type(self) is type(other) and self.bit_rate == other.bit_rate

    def __gt__(self, other):
        return type(self) is type(other) and self.bit_rate > other.bit_rate


class Mp3Codec(BitRateMixin, BaseCodec):

    SUPPORTED_MIME_TYPES = ['audio/mpeg', 'audio/mp3']
    IDENTIFIER = 'mp3'
    ENCODERS = {
        'generic': pulseaudio_dlna.encoders.LameMp3Encoder,
        'ffmpeg': pulseaudio_dlna.encoders.FFMpegMp3Encoder,
        'avconv': pulseaudio_dlna.encoders.AVConvMp3Encoder,
    }
    PRIORITY = 18

    def __init__(self, mime_string=None):
        BaseCodec.__init__(self)
        BitRateMixin.__init__(self)
        self.suffix = 'mp3'
        self.mime_type = mime_string or 'audio/mp3'


class WavCodec(BaseCodec):

    SUPPORTED_MIME_TYPES = ['audio/wav', 'audio/x-wav']
    IDENTIFIER = 'wav'
    ENCODERS = {
        'generic': pulseaudio_dlna.encoders.SoxWavEncoder,
        'ffmpeg': pulseaudio_dlna.encoders.FFMpegWavEncoder,
        'avconv': pulseaudio_dlna.encoders.AVConvWavEncoder,
        'pulseaudio': pulseaudio_dlna.encoders.NullEncoder,
    }
    PRIORITY = 15

    def __init__(self, mime_string=None):
        BaseCodec.__init__(self)
        self.suffix = 'wav'
        self.mime_type = mime_string or 'audio/wav'


class L16Codec(BaseCodec):

    SUPPORTED_MIME_TYPES = ['audio/l16']
    IDENTIFIER = 'l16'
    ENCODERS = {
        'generic': pulseaudio_dlna.encoders.SoxL16Encoder,
        'ffmpeg': pulseaudio_dlna.encoders.FFMpegL16Encoder,
        'avconv': pulseaudio_dlna.encoders.AVConvL16Encoder,
    }
    PRIORITY = 1

    def __init__(self, mime_string=None):
        BaseCodec.__init__(self)
        self.suffix = 'pcm16'
        self.mime_type = 'audio/L16'

        self.sample_rate = None
        self.channels = None

        if mime_string:
            match = re.match(
                '(.*?)(?P<mime_type>.*?);'
                '(.*?)rate=(?P<sample_rate>.*?);'
                '(.*?)channels=(?P<channels>\d)', mime_string)
            if match:
                self.mime_type = match.group('mime_type')
                self.sample_rate = int(match.group('sample_rate'))
                self.channels = int(match.group('channels'))

    @property
    def specific_mime_type(self):
        if self.sample_rate and self.channels:
            return '{};rate={};channels={}'.format(
                self.mime_type, self.sample_rate, self.channels)
        else:
            return self.mime_type

    @property
    def encoder(self):
        return self.encoder_type(self.sample_rate, self.channels)

    def __eq__(self, other):
        return type(self) is type(other) and (
            self.sample_rate == other.sample_rate and
            self.channels == other.channels)

    def __gt__(self, other):
        return type(self) is type(other) and (
            self.sample_rate > other.sample_rate and
            self.channels > other.channels)


class AacCodec(BitRateMixin, BaseCodec):

    SUPPORTED_MIME_TYPES = ['audio/aac', 'audio/x-aac']
    IDENTIFIER = 'aac'
    ENCODERS = {
        'generic': pulseaudio_dlna.encoders.FaacAacEncoder,
        'ffmpeg': pulseaudio_dlna.encoders.FFMpegAacEncoder,
        'avconv': pulseaudio_dlna.encoders.AVConvAacEncoder,
    }
    PRIORITY = 12

    def __init__(self, mime_string=None):
        BaseCodec.__init__(self)
        BitRateMixin.__init__(self)
        self.suffix = 'aac'
        self.mime_type = mime_string or 'audio/aac'


class OggCodec(BitRateMixin, BaseCodec):

    SUPPORTED_MIME_TYPES = ['audio/ogg', 'audio/x-ogg', 'application/ogg']
    IDENTIFIER = 'ogg'
    ENCODERS = {
        'generic': pulseaudio_dlna.encoders.OggencOggEncoder,
        'ffmpeg': pulseaudio_dlna.encoders.FFMpegOggEncoder,
        'avconv': pulseaudio_dlna.encoders.AVConvOggEncoder,
        'pulseaudio': pulseaudio_dlna.encoders.NullEncoder,
    }
    PRIORITY = 6

    def __init__(self, mime_string=None):
        BaseCodec.__init__(self)
        BitRateMixin.__init__(self)
        self.suffix = 'ogg'
        self.mime_type = mime_string or 'audio/ogg'


class FlacCodec(BaseCodec):

    SUPPORTED_MIME_TYPES = ['audio/flac', 'audio/x-flac']
    IDENTIFIER = 'flac'
    ENCODERS = {
        'generic': pulseaudio_dlna.encoders.FlacFlacEncoder,
        'ffmpeg': pulseaudio_dlna.encoders.FFMpegFlacEncoder,
        'avconv': pulseaudio_dlna.encoders.AVConvFlacEncoder,
        'pulseaudio': pulseaudio_dlna.encoders.NullEncoder,
    }
    PRIORITY = 9

    def __init__(self, mime_string=None):
        BaseCodec.__init__(self)
        self.suffix = 'flac'
        self.mime_type = mime_string or 'audio/flac'


class OpusCodec(BitRateMixin, BaseCodec):

    SUPPORTED_MIME_TYPES = ['audio/opus', 'audio/x-opus']
    IDENTIFIER = 'opus'
    ENCODERS = {
        'generic': pulseaudio_dlna.encoders.OpusencOpusEncoder,
        'ffmpeg': pulseaudio_dlna.encoders.FFMpegOpusEncoder,
        'avconv': pulseaudio_dlna.encoders.AVConvOpusEncoder,
    }
    PRIORITY = 3

    def __init__(self, mime_string=None):
        BaseCodec.__init__(self)
        BitRateMixin.__init__(self)
        self.suffix = 'opus'
        self.mime_type = mime_string or 'audio/opus'


def load_codecs():
    if len(CODECS) == 0:
        logger.debug('Loaded codecs:')
        for name, _type in inspect.getmembers(sys.modules[__name__]):
            if inspect.isclass(_type) and issubclass(_type, BaseCodec):
                if _type is not BaseCodec:
                    logger.debug('  {} = {}'.format(_type.IDENTIFIER, _type))
                    CODECS[_type.IDENTIFIER] = _type
    return None


load_codecs()
