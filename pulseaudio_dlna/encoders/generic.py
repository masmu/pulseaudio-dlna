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

import logging

from pulseaudio_dlna.encoders import (
    BitRateMixin, SamplerateChannelMixin, BaseEncoder)

logger = logging.getLogger('pulseaudio_dlna.encoder.generic')


class LameMp3Encoder(BitRateMixin, BaseEncoder):

    SUPPORTED_BIT_RATES = [32, 40, 48, 56, 64, 80, 96, 112,
                           128, 160, 192, 224, 256, 320]

    def __init__(self, bit_rate=None):
        BaseEncoder.__init__(self)
        self.bit_rate = bit_rate or LameMp3Encoder.DEFAULT_BIT_RATE

        self._writes_header = False
        self._binary = 'lame'
        self._command = ['-b', str(self.bit_rate), '-r', '-']


class SoxWavEncoder(BaseEncoder):
    def __init__(self):
        BaseEncoder.__init__(self)

        self._writes_header = True
        self._binary = 'sox'
        self._command = ['-t', 'raw', '-b', '16', '-e', 'signed', '-c', '2',
                         '-r', '44100', '-',
                         '-t', 'wav', '-b', '16', '-e', 'signed', '-c', '2',
                         '-r', '44100',
                         '-L', '-',
                         ]


class SoxL16Encoder(SamplerateChannelMixin, BaseEncoder):
    def __init__(self, sample_rate=None, channels=None):
        BaseEncoder.__init__(self)
        self.sample_rate = sample_rate or 44100
        self.channels = channels or 2

        self._writes_header = True
        self._binary = 'sox'
        self._command = ['-t', 'raw', '-b', '16', '-e', 'signed', '-c', '2',
                         '-r', '44100', '-',
                         '-t', 'wav', '-b', '16', '-e', 'signed',
                         '-c', str(self.channels),
                         '-r', '44100',
                         '-B', '-',
                         'rate', str(self.sample_rate),
                         ]


class FaacAacEncoder(BitRateMixin, BaseEncoder):

    SUPPORTED_BIT_RATES = [32, 40, 48, 56, 64, 80, 96, 112,
                           128, 160, 192, 224, 256, 320]

    def __init__(self, bit_rate=None):
        BaseEncoder.__init__(self)
        self.bit_rate = bit_rate or FaacAacEncoder.DEFAULT_BIT_RATE

        self._writes_header = None
        self._binary = 'faac'
        self._command = ['-b', str(self.bit_rate),
                         '-X', '-P', '-o', '-', '-']


class OggencOggEncoder(BitRateMixin, BaseEncoder):

    SUPPORTED_BIT_RATES = [32, 40, 48, 56, 64, 80, 96, 112,
                           128, 160, 192, 224, 256, 320]

    def __init__(self, bit_rate=None):
        BaseEncoder.__init__(self)
        self.bit_rate = bit_rate or OggencOggEncoder.DEFAULT_BIT_RATE

        self._writes_header = True
        self._binary = 'oggenc'
        self._command = ['-b', str(self.bit_rate),
                         '-Q', '-r', '--ignorelength', '-']


class FlacFlacEncoder(BaseEncoder):

    def __init__(self, bit_rate=None):
        BaseEncoder.__init__(self)

        self._writes_header = True
        self._binary = 'flac'
        self._command = ['-', '-c', '--channels', '2', '--bps', '16',
                         '--sample-rate', '44100',
                         '--endian', 'little', '--sign', 'signed', '-s']


class OpusencOpusEncoder(BitRateMixin, BaseEncoder):

    SUPPORTED_BIT_RATES = [i for i in range(6, 257)]

    def __init__(self, bit_rate=None):
        BaseEncoder.__init__(self)
        self.bit_rate = bit_rate or OpusencOpusEncoder.DEFAULT_BIT_RATE

        self._writes_header = True
        self._binary = 'opusenc'
        self._command = ['--bitrate', str(self.bit_rate),
                         '--padding', '0', '--max-delay', '0',
                         '--expect-loss', '1', '--framesize', '2.5',
                         '--raw-rate', '44100',
                         '--raw', '-', '-']
