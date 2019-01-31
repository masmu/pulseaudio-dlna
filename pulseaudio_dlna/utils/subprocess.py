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

from gi.repository import GObject

import subprocess
import threading
import os
import sys
import logging

logger = logging.getLogger('pulseaudio_dlna.utils.subprocess')


class Subprocess(subprocess.Popen):
    def __init__(self, cmd, uid=None, gid=None, cwd=None, env=None,
                 *args, **kwargs):

        self.uid = uid
        self.gid = gid
        self.cwd = cwd
        self.env = env

        super(Subprocess, self).__init__(
            cmd,
            preexec_fn=self.demote(uid, gid), cwd=cwd, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            bufsize=1)

    def demote(self, uid, gid):
        def fn_uid_gid():
            os.setgid(gid)
            os.setuid(uid)

        def fn_uid():
            os.setuid(uid)

        def fn_gid():
            os.setgid(gid)

        def fn_nop():
            pass

        if uid and gid:
            return fn_uid_gid
        elif uid:
            return fn_uid
        elif gid:
            return fn_gid
        return fn_nop


class GobjectMainLoopMixin(object):
    def __init__(self, *args, **kwargs):
        super(GobjectMainLoopMixin, self).__init__(*args, **kwargs)
        for pipe in [self.stdout, self.stderr]:
            GObject.io_add_watch(
                pipe, GObject.IO_IN | GObject.IO_PRI, self._on_new_data)

    def _on_new_data(self, fd, condition):
        line = fd.readline().decode('utf-8')
        sys.stdout.write(line)
        sys.stdout.flush()
        return True


class ThreadedMixIn(object):
    def __init__(self, *args, **kwargs):
        super(ThreadedMixIn, self).__init__(*args, **kwargs)
        self.init_thread(self.stdout)
        self.init_thread(self.stderr)

    def init_thread(self, pipe):
        def read_all(pipe):
            with pipe:
                for line in iter(pipe.readline, ''):
                    sys.stdout.write(line)
                    sys.stdout.flush()

        t = threading.Thread(target=read_all, args=(pipe, ))
        t.daemon = True
        t.start()


class ThreadedSubprocess(ThreadedMixIn, Subprocess):
    pass


class GobjectSubprocess(GobjectMainLoopMixin, Subprocess):
    pass
