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

import pulseaudio_dlna.codecs


class BaseRecorder(object):
    def __init__(self):
        self._command = []

    @property
    def command(self):
        return self._command


class PulseaudioRecorder(BaseRecorder):
    def __init__(self, monitor, codec=None):
        BaseRecorder.__init__(self)
        self._monitor = monitor
        self._codec = codec
        self._command = ['parec', '--format=s16le']

    @property
    def monitor(self):
        return self._monitor

    @property
    def codec(self):
        return self._codec

    @property
    def file_format(self):
        if isinstance(self.codec, pulseaudio_dlna.codecs.WavCodec):
            return 'wav'
        elif isinstance(self.codec, pulseaudio_dlna.codecs.OggCodec):
            return 'oga'
        elif isinstance(self.codec, pulseaudio_dlna.codecs.FlacCodec):
            return 'flac'
        return None

    @property
    def command(self):
        if not self.codec:
            return super(PulseaudioRecorder, self).command + ['-d', self.monitor]
        else:
            return super(PulseaudioRecorder, self).command + [
                '-d', self.monitor,
                '--file-format={}'.format(self.file_format),
            ]
