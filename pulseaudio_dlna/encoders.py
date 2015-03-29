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
        self._mime_types = []
        self._suffix = 'undefined'

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


class AacEncoder(BaseEncoder):
    def __init__(self):
        BaseEncoder.__init__(self)
        self._command = 'faac -P -b 320 -X -o - -'
        self._mime_type = 'audio/aac'
        self._suffix = 'aac'
        self._mime_types = ['audio/mp4', 'audio/aac', 'audio/x-aac']


class LameEncoder(BaseEncoder):
    def __init__(self):
        BaseEncoder.__init__(self)
        self._command = 'lame -r -b 320 -'
        self._mime_type = 'audio/mpeg'
        self._suffix = 'mp3'
        self._mime_types = ['audio/mpeg', 'audio/mp3']


class FlacEncoder(BaseEncoder):
    def __init__(self):
        BaseEncoder.__init__(self)
        self._command = 'flac - -c --channels 2 --bps 16 --sample-rate 44100 --endian little --sign signed'
        self._mime_type = 'audio/flac'
        self._suffix = 'flac'
        self._mime_types = ['audio/flac', 'audio/x-flac']


class OggEncoder(BaseEncoder):
    def __init__(self):
        BaseEncoder.__init__(self)
        self._command = 'oggenc -Q -r -k --ignorelength -'
        self._mime_type = 'audio/ogg'
        self._suffix = 'ogg'
        self._mime_types = ['audio/ogg', 'audio/x-ogg']


class OpusEncoder(BaseEncoder):
    def __init__(self):
        BaseEncoder.__init__(self)
        self._command = 'opusenc --padding 0 --max-delay 0 --expect-loss 1 --framesize 2.5 --raw-rate 44100 --raw --bitrate 64 - -'
        self._mime_type = 'audio/opus'
        self._suffix = 'opus'
        self._mime_types = ['audio/opus', 'audio/x-opus']


class WavEncoder(BaseEncoder):
    def __init__(self):
        BaseEncoder.__init__(self)
        self._command = 'sox -t raw -b 16 -e signed -c 2 -r 44100 - -t wav -r 44100 -b 16 -L -e signed -c 2 -'
        self._mime_type = 'audio/wav'
        self._suffix = 'wav'
        self._mime_types = ['audio/wav', 'audio/x-wav']

# MP4Encoder
