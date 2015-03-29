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


class BaseEncoder(object):
    def __init__(self):
        self._command = ''
        self._mime_type = 'undefined'
        self._suffix = 'undefined'

    @property
    def command(self):
        return self._command

    @property
    def mime_type(self):
        return self._mime_type

    @property
    def suffix(self):
        return self._suffix


class LameEncoder(BaseEncoder):
    def __init__(self):
        BaseEncoder.__init__(self)
        self._command = 'lame -r -b 320 -'
        self._mime_type = 'audio/mpeg'
        self._suffix = 'mp3'


class FlacEncoder(BaseEncoder):
    def __init__(self):
        BaseEncoder.__init__(self)
        self._command = 'flac - -c --channels 2 --bps 16 --sample-rate 44100 --endian little --sign signed'
        self._mime_type = 'audio/flac'
        self._suffix = 'flac'


class OggEncoder(BaseEncoder):
    def __init__(self):
        BaseEncoder.__init__(self)
        self._command = 'oggenc -r -'
        self._mime_type = 'audio/ogg'
        self._suffix = 'ogg'


class OpusEncoder(BaseEncoder):
    def __init__(self):
        BaseEncoder.__init__(self)
        self._command = 'opusenc --padding 0 --max-delay 0 --expect-loss 1 --framesize 2.5 --raw-rate 44100 --raw --bitrate 64 - -'
        self._mime_type = 'audio/opus'
        self._suffix = 'opus'


class WavEncoder(BaseEncoder):
    def __init__(self):
        BaseEncoder.__init__(self)
        self._command = 'sox -t raw -b 16 -e signed -c 2 -r 44100 - -t wav -r 44100 -b 16 -L -e signed -c 2 -'
        self._mime_type = 'audio/wav'
        self._suffix = 'wav'
