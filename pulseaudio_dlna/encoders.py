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

import distutils.spawn
import inspect
import sys
import logging

logger = logging.getLogger('pulseaudio_dlna.encoder')

ENCODERS = []


class InvalidBitrateException():
    pass


class UnsupportedBitrateException():
    pass


class UnsupportedMimeTypeException():
    pass


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
            result = distutils.spawn.find_executable(self.binary)
            if result is not None and result.endswith(self.binary):
                type(self).AVAILABLE = True
        return type(self).AVAILABLE

    @property
    def supported_bit_rates(self):
        raise UnsupportedBitrateException()

    def __str__(self):
        return '<{} available="{}">'.format(
            self.__class__.__name__,
            unicode(self.available),
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
            unicode(self.available),
            unicode(self.bit_rate),
        )


class NullEncoder(BaseEncoder):

    def __init__(self):
        BaseEncoder.__init__(self)
        self._binary = 'cat'
        self._command = []


class FFMpegMixin(object):

    def _ffmpeg_command(
            self, format, bit_rate=None, sample_rate=None, channels=None):
        command = [
            '-loglevel', 'panic',
        ]
        command.extend([
            '-ac', '2',
            '-ar', '44100',
            '-f', 's16le',
            '-i', '-',
        ])
        command.extend([
            '-strict', '-2',
            '-f', format,
        ])
        if bit_rate:
            command.extend(['-b:a', str(bit_rate) + 'k'])
        if sample_rate:
            command.extend(['-ar', str(sample_rate)])
        if channels:
            command.extend(['-ac', str(channels)])
        command.append('pipe:')
        return command


class FFMpegMp3Encoder(BitRateMixin, FFMpegMixin, BaseEncoder):

    SUPPORTED_BIT_RATES = [32, 40, 48, 56, 64, 80, 96, 112,
                           128, 160, 192, 224, 256, 320]

    def __init__(self, bit_rate=None):
        BaseEncoder.__init__(self)
        self.bit_rate = bit_rate or FFMpegMp3Encoder.DEFAULT_BIT_RATE

        self._writes_header = True
        self._binary = 'ffmpeg'
        self._command = self._ffmpeg_command('mp3', bit_rate=self.bit_rate)


class FFMpegWavEncoder(FFMpegMixin, BaseEncoder):

    def __init__(self, bit_rate=None):
        BaseEncoder.__init__(self)

        self._writes_header = True
        self._binary = 'ffmpeg'
        self._command = self._ffmpeg_command('wav')


class FFMpegL16Encoder(FFMpegMixin, BaseEncoder):
    def __init__(self, sample_rate=None, channels=None):
        BaseEncoder.__init__(self)
        self._sample_rate = sample_rate or 44100
        self._channels = channels or 2

        self._writes_header = None
        self._binary = 'ffmpeg'
        self._command = self._ffmpeg_command(
            's16be', sample_rate=self.sample_rate, channels=self.channels)

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
            unicode(self.available),
            unicode(self.sample_rate),
            unicode(self.channels),
        )


class FFMpegAacEncoder(BitRateMixin, FFMpegMixin, BaseEncoder):

    SUPPORTED_BIT_RATES = [32, 40, 48, 56, 64, 80, 96, 112,
                           128, 160, 192, 224, 256, 320]

    def __init__(self, bit_rate=None):
        BaseEncoder.__init__(self)
        self.bit_rate = bit_rate or FFMpegAacEncoder.DEFAULT_BIT_RATE

        self._writes_header = False
        self._binary = 'ffmpeg'
        self._command = self._ffmpeg_command('adts', bit_rate=self.bit_rate)


class FFMpegOggEncoder(BitRateMixin, FFMpegMixin, BaseEncoder):

    SUPPORTED_BIT_RATES = [32, 40, 48, 56, 64, 80, 96, 112,
                           128, 160, 192, 224, 256, 320]

    def __init__(self, bit_rate=None):
        BaseEncoder.__init__(self)
        self.bit_rate = bit_rate or FFMpegOggEncoder.DEFAULT_BIT_RATE

        self._writes_header = True
        self._binary = 'ffmpeg'
        self._command = self._ffmpeg_command('ogg', bit_rate=self.bit_rate)


class FFMpegFlacEncoder(FFMpegMixin, BaseEncoder):

    def __init__(self, bit_rate=None):
        BaseEncoder.__init__(self)

        self._writes_header = True
        self._binary = 'ffmpeg'
        self._command = self._ffmpeg_command('flac')


class FFMpegOpusEncoder(BitRateMixin, FFMpegMixin, BaseEncoder):

    SUPPORTED_BIT_RATES = [i for i in range(6, 257)]

    def __init__(self, bit_rate=None):
        BaseEncoder.__init__(self)
        self.bit_rate = bit_rate or FFMpegOpusEncoder.DEFAULT_BIT_RATE

        self._writes_header = True
        self._binary = 'ffmpeg'
        self._command = self._ffmpeg_command('opus', bit_rate=self.bit_rate)


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
