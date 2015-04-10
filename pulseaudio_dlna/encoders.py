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


class UnsupportedBitrateException():
    pass


class BaseEncoder(object):
    def __init__(self):
        self._command = ''
        self._mime_type = 'undefined'
        self._mime_types = []
        self._suffix = 'undefined'
        self._bit_rate = None
        self._bit_rates = []

    @property
    def command(self):
        return self._command

    @property
    def mime_type(self):
        return self._mime_type

    @property
    def mime_types(self):
        return self._mime_types

    @property
    def suffix(self):
        return self._suffix

    @property
    def bit_rate(self):
        return self._bit_rate

    @bit_rate.setter
    def bit_rate(self, value):
        if int(value) in self.bit_rates:
            self._bit_rate = value
        else:
            raise UnsupportedBitrateException()

    @property
    def bit_rates(self):
        return self._bit_rates

    def __str__(self):
        return '<{} bit-rate="{}" mime-types="{}">'.format(
            self.__class__.__name__,
            str(self.bit_rate),
            ','.join(self.mime_types),
        )


class WavEncoder(BaseEncoder):
    def __init__(self):
        BaseEncoder.__init__(self)
        self._command = ('sox -t raw -b 16 -e signed -c 2 -r 44100 - -t wav '
                         '-r 44100 -b 16 -L -e signed -c 2 -')
        self._mime_type = 'audio/wav'
        self._suffix = 'wav'
        self._mime_types = ['audio/wav', 'audio/x-wav']
        self._bit_rate = None
        self._bit_rates = []

    @property
    def bit_rate(self):
        return self._bit_rate

    @bit_rate.setter
    def bit_rate(self, value):
        raise UnsupportedBitrateException()


class LameEncoder(BaseEncoder):
    def __init__(self):
        BaseEncoder.__init__(self)
        self._command = 'lame {bit_rate} -r -'
        self._mime_type = 'audio/mpeg'
        self._suffix = 'mp3'
        self._mime_types = ['audio/mpeg', 'audio/mp3']
        self._bit_rate = 192
        self._bit_rates = [32, 40, 48, 56, 64, 80, 96, 112,
                           128, 160, 192, 224, 256, 320]

    @property
    def command(self):
        if self.bit_rate is None:
            return self._command.format(bit_rate='')
        else:
            return self._command.format(bit_rate='-b ' + str(self.bit_rate))


class AacEncoder(BaseEncoder):
    def __init__(self):
        BaseEncoder.__init__(self)
        self._command = 'faac {bit_rate} -X -P -o - -'
        self._mime_type = 'audio/aac'
        self._suffix = 'aac'
        self._mime_types = ['audio/aac', 'audio/x-aac']
        self._bit_rates = [32, 40, 48, 56, 64, 80, 96, 112,
                           128, 160, 192, 224, 256, 320]
        self._bit_rate = 192

    @property
    def command(self):
        if self.bit_rate is None:
            return self._command.format(bit_rate='')
        else:
            return self._command.format(bit_rate='-b ' + str(self.bit_rate))


class FlacEncoder(BaseEncoder):
    def __init__(self):
        BaseEncoder.__init__(self)
        self._command = ('flac - -c --channels 2 --bps 16 --sample-rate 44100 '
                         '--endian little --sign signed -s')
        self._mime_type = 'audio/flac'
        self._suffix = 'flac'
        self._mime_types = ['audio/flac', 'audio/x-flac']
        self._bit_rate = None
        self._bit_rates = []

    @property
    def bit_rate(self):
        return self._bit_rate

    @bit_rate.setter
    def bit_rate(self, value):
        raise UnsupportedBitrateException()


class OggEncoder(BaseEncoder):
    def __init__(self):
        BaseEncoder.__init__(self)
        self._command = 'oggenc {bit_rate} -Q -r -k --ignorelength -'
        self._mime_type = 'audio/ogg'
        self._suffix = 'ogg'
        self._mime_types = ['audio/ogg', 'audio/x-ogg']
        self._bit_rate = 192

    @property
    def bit_rate(self):
        return self._bit_rate

    @bit_rate.setter
    def bit_rate(self, value):
        self._bit_rate = int(value)

    @property
    def command(self):
        if self.bit_rate is None:
            return self._command.format(bit_rate='')
        else:
            return self._command.format(bit_rate='-b ' + str(self.bit_rate))


class OpusEncoder(BaseEncoder):
    def __init__(self):
        BaseEncoder.__init__(self)
        self._command = ('opusenc {bit_rate} --padding 0 --max-delay 0 '
                         '--expect-loss 1 --framesize 2.5 --raw-rate 44100 '
                         '--raw --bitrate 64 - -')
        self._mime_type = 'audio/opus'
        self._suffix = 'opus'
        self._mime_types = ['audio/opus', 'audio/x-opus']
        self._bit_rate = 192
        self._bit_rates = [i for i in range(6, 257)]

    @property
    def command(self):
        if self.bit_rate is None:
            return self._command.format(bit_rate='')
        else:
            return self._command.format(bit_rate='--bitrate ' + str(self.bit_rate))
