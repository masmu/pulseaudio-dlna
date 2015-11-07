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

from __future__ import absolute_import
from __future__ import unicode_literals

from psutil import *

_Process = Process
class ShimmedProcess(Process):

    def uids(self):
        return _Process.uids(self)

    def gids(self):
        return _Process.gids(self)

    def name(self):
        return _Process.name(self)

Process = ShimmedProcess

_process_iter = process_iter

def Shimmed_process_iter():
    for proc in _process_iter():
        proc.__class__ = ShimmedProcess
        yield proc

process_iter = Shimmed_process_iter
