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

import distutils.spawn
import inspect
import sys
import logging

logger = logging.getLogger('pulseaudio_dlna.encoder')

ENCODERS = []


class InvalidBitrateException(Exception):
    def __init__(self, bit_rate):
        Exception.__init__(
            self,
            'You specified an invalid bit rate "{}"!'.format(bit_rate),
        )


class UnsupportedBitrateException(Exception):
    def __init__(self, bit_rate, cls):
        Exception.__init__(
            self,
            'You specified an unsupported bit rate for the {encoder}! '
            'Supported bit rates are "{bit_rates}"! '.format(
                encoder=cls.__name__,
                bit_rates=','.join(
                    str(e) for e in cls.SUPPORTED_BIT_RATES
                )
            )
        )


def set_bit_rate(bit_rate):
    try:
        bit_rate = int(bit_rate)
    except ValueError:
        raise InvalidBitrateException(bit_rate)

    for _type in ENCODERS:
        if hasattr(_type, 'DEFAULT_BIT_RATE') and \
           hasattr(_type, 'SUPPORTED_BIT_RATES'):
            if bit_rate in _type.SUPPORTED_BIT_RATES:
                _type.DEFAULT_BIT_RATE = bit_rate


def _find_executable(path):
    # The distutils module uses python's ascii default encoding and is
    # therefore not capable of handling unicode properly when it contains
    # non-ascii characters.
    result = distutils.spawn.find_executable(path)
    return result


class BaseEncoder(object):

    AVAILABLE = True

    def __init__(self):
        self._binary = None
        self._command = []
        self._bit_rate = None
        self._writes_header = False

    @property
    def binary(self):
        return self._binary

    @property
    def command(self):
        return [self.binary] + self._command

    @property
    def available(self):
        return type(self).AVAILABLE

    @property
    def writes_header(self):
        return self._writes_header

    def validate(self):
        if not type(self).AVAILABLE:
            result = _find_executable(self.binary)
            if result is not None and result.endswith(self.binary):
                type(self).AVAILABLE = True
        return type(self).AVAILABLE

    @property
    def supported_bit_rates(self):
        raise UnsupportedBitrateException()

    def __str__(self):
        return '<{} available="{}">'.format(
            self.__class__.__name__,
            str(self.available),
        )


class BitRateMixin(object):

    DEFAULT_BIT_RATE = 192

    @property
    def bit_rate(self):
        return self._bit_rate

    @bit_rate.setter
    def bit_rate(self, value):
        if int(value) in self.SUPPORTED_BIT_RATES:
            self._bit_rate = value
        else:
            raise UnsupportedBitrateException()

    @property
    def supported_bit_rates(self):
        return self.SUPPORTED_BIT_RATES

    def __str__(self):
        return '<{} available="{}" bit-rate="{}">'.format(
            self.__class__.__name__,
            str(self.available),
            str(self.bit_rate),
        )


class SamplerateChannelMixin(object):

    @property
    def sample_rate(self):
        return self._sample_rate

    @sample_rate.setter
    def sample_rate(self, value):
        self._sample_rate = int(value)

    @property
    def channels(self):
        return self._channels

    @channels.setter
    def channels(self, value):
        self._channels = int(value)

    def __str__(self):
        return '<{} available="{}" sample-rate="{}" channels="{}">'.format(
            self.__class__.__name__,
            str(self.available),
            str(self.sample_rate),
            str(self.channels),
        )


class NullEncoder(BaseEncoder):

    def __init__(self, *args, **kwargs):
        BaseEncoder.__init__(self)
        self._binary = 'cat'
        self._command = []


from pulseaudio_dlna.encoders.generic import *
from pulseaudio_dlna.encoders.ffmpeg import *
from pulseaudio_dlna.encoders.avconv import *


def load_encoders():
    if len(ENCODERS) == 0:
        logger.debug('Loaded encoders:')
        for name, _type in inspect.getmembers(sys.modules[__name__]):
            if inspect.isclass(_type) and issubclass(_type, BaseEncoder):
                if _type is not BaseEncoder:
                    logger.debug('  {}'.format(_type))
                    ENCODERS.append(_type)
    return None


load_encoders()
