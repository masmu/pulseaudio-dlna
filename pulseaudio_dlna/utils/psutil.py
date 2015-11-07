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

import logging
import psutil

logger = logging.getLogger('pulseaudio_dlna.utils.psutil')


__series__ = int(psutil.__version__[:1])

if __series__ >= 2:
    NoSuchProcess = psutil.NoSuchProcess
    TimeoutExpired = psutil.TimeoutExpired
else:
    NoSuchProcess = psutil._error.NoSuchProcess
    TimeoutExpired = psutil._error.TimeoutExpired


def wait_procs(*args, **kwargs):
    return psutil.wait_procs(*args, **kwargs)


def process_iter(*args, **kwargs):
    processes = []
    for p in psutil.process_iter(*args, **kwargs):
        p.__class__ = Process
        processes.append(p)
    return processes


class Process(psutil.Process):
    def __init__(self, *args, **kwargs):
        psutil.Process.__init__(self, *args, **kwargs)

    def name(self):
        if __series__ >= 2:
            return psutil.Process.name(self)
        else:
            return self._platform_impl.get_process_name()

    def uids(self):
        if __series__ >= 2:
            return psutil.Process.uids(self)
        else:
            return self._platform_impl.get_process_uids()

    def gids(self):
        if __series__ >= 2:
            return psutil.Process.gids(self)
        else:
            return self._platform_impl.get_process_gids()
