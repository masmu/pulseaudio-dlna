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


class BaseRecorder(object):
    def __init__(self):
        self._command = []

    @property
    def command(self):
        return self._command


class PulseaudioRecorder(BaseRecorder):
    def __init__(self, monitor, _format=None):
        BaseRecorder.__init__(self)
        self._monitor = monitor
        self._format = _format
        self._command = ['parec', '--format=s16le']

    @property
    def monitor(self):
        return self._monitor

    @property
    def format(self):
        return self._format

    @property
    def command(self):
        if not self.format:
            return super(PulseaudioRecorder, self).command + ['-d', self.monitor]
        else:
            return super(PulseaudioRecorder, self).command + [
                '-d', self.monitor, '--file-format=' + self.format]
