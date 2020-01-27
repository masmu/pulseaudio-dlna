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

from pulseaudio_dlna.encoders.ffmpeg import (
    FFMpegMp3Encoder, FFMpegWavEncoder, FFMpegL16Encoder, FFMpegAacEncoder,
    FFMpegOggEncoder, FFMpegFlacEncoder, FFMpegOpusEncoder)

logger = logging.getLogger('pulseaudio_dlna.encoder.avconv')


class AVConvMp3Encoder(FFMpegMp3Encoder):

    def __init__(self, bit_rate=None):
        super(AVConvMp3Encoder, self).__init__(bit_rate=bit_rate)
        self._binary = 'avconv'


class AVConvWavEncoder(FFMpegWavEncoder):

    def __init__(self, bit_rate=None):
        super(AVConvWavEncoder, self).__init__()
        self._binary = 'avconv'


class AVConvL16Encoder(FFMpegL16Encoder):

    def __init__(self, sample_rate=None, channels=None):
        super(AVConvL16Encoder, self).__init__(
            sample_rate=sample_rate, channels=channels)
        self._binary = 'avconv'


class AVConvAacEncoder(FFMpegAacEncoder):

    def __init__(self, bit_rate=None):
        super(AVConvAacEncoder, self).__init__(bit_rate=bit_rate)
        self._binary = 'avconv'


class AVConvOggEncoder(FFMpegOggEncoder):

    def __init__(self, bit_rate=None):
        super(AVConvOggEncoder, self).__init__(bit_rate=bit_rate)
        self._binary = 'avconv'


class AVConvFlacEncoder(FFMpegFlacEncoder):

    def __init__(self, bit_rate=None):
        super(AVConvFlacEncoder, self).__init__()
        self._binary = 'avconv'


class AVConvOpusEncoder(FFMpegOpusEncoder):

    def __init__(self, bit_rate=None):
        super(AVConvOpusEncoder, self).__init__(bit_rate=bit_rate)
        self._binary = 'avconv'
