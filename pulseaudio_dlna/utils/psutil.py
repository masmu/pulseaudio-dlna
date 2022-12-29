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
import psutil

logger = logging.getLogger('pulseaudio_dlna.utils.psutil')


__series__ = int(psutil.__version__[:1])

NoSuchProcess = psutil.NoSuchProcess
TimeoutExpired = psutil.TimeoutExpired


def wait_procs(*args, **kwargs):
    return psutil.wait_procs(*args, **kwargs)


def process_iter(*args, **kwargs):
    for p in psutil.process_iter(*args, **kwargs):
        p.__class__ = Process
        yield p


if __series__ >= 2:
    class Process(psutil.Process):
        pass
else:
    class Process(psutil.Process):

        def children(self, *args, **kwargs):
            return self.get_children(*args, **kwargs)

        def name(self):
            return self._platform_impl.get_process_name()

        def uids(self):
            return self._platform_impl.get_process_uids()

        def gids(self):
            return self._platform_impl.get_process_gids()
