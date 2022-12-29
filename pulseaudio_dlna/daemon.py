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

import dbus
import dbus.mainloop.glib
import logging
import os
import sys
import setproctitle
import functools
import signal
import pwd

import pulseaudio_dlna.utils.subprocess
import pulseaudio_dlna.utils.psutil as psutil

logger = logging.getLogger('pulseaudio_dlna.daemon')


REQUIRED_ENVIRONMENT_VARS = [
    'DISPLAY',
    'DBUS_SESSION_BUS_ADDRESS',
    'PATH',
    'XDG_RUNTIME_DIR',
    'LANG'
]


def missing_env_vars(environment):
    env = []
    for var in REQUIRED_ENVIRONMENT_VARS:
        if var not in environment:
            env.append(var)
    return env


class Daemon(object):
    def __init__(self):
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        setproctitle.setproctitle('pulseaudio-daemon')
        self.mainloop = GObject.MainLoop()
        self.processes = []
        self.check_id = None
        self.is_checking = False

        self._check_processes()

        signals = (
            ('NameOwnerChanged', 'org.freedesktop.DBus.{}',
                self.on_name_owner_changed),
        )
        self.bus = dbus.SystemBus()
        self.core = self.bus.get_object('org.freedesktop.DBus', '/')
        for sig_name, interface, sig_handler in signals:
            self.bus.add_signal_receiver(sig_handler, sig_name)

    def shutdown(self, signal_number=None, frame=None):
        logger.info('Daemon.shutdown')
        for proc in self.processes:
            if proc.is_attached:
                proc.detach()
        self.processes = []

    def on_name_owner_changed(self, name, new_owner, old_owner):
        if not self.is_checking:
            if self.check_id:
                GObject.source_remove(self.check_id)
            self.check_id = GObject.timeout_add(
                3000, self._check_processes)

    def _check_processes(self):
        self.is_checking = True
        self.check_id = None
        logger.info('Checking pulseaudio processes ...')

        procs = PulseAudioFinder.get_processes()
        for proc in procs:
            if proc not in self.processes:
                logger.info('Adding pulseaudio process ({})'.format(proc.pid))
                self.processes.append(proc)

        gone, alive = psutil.wait_procs(self.processes, timeout=2)
        for proc in gone:
            if proc.is_attached:
                proc.detach()
            logger.info('Removing pulseaudio process ({})'.format(proc.pid))
            self.processes.remove(proc)
        for proc in alive:
            if not proc.is_attached and not proc.disabled:
                proc.attach()

        self.is_checking = False
        return False

    def run(self):
        try:
            self.mainloop.run()
        except KeyboardInterrupt:
            self.shutdown()


@functools.total_ordering
class PulseAudioProcess(psutil.Process):

    DISPLAY_MANAGERS = ['gdm', 'lightdm', 'kdm', None]
    UID_MIN = 500

    def __init__(self, *args, **kwargs):
        psutil.Process.__init__(*args, **kwargs)
        self.application = None
        self.disabled = False

    @property
    def env(self):
        return self._get_proc_env(self.pid)

    @property
    def compressed_env(self):
        env = {}
        if self.env:
            for k in REQUIRED_ENVIRONMENT_VARS:
                if k in self.env:
                    env[k] = self.env[k]
        return env

    @property
    def uid(self):
        return self.uids()[0]

    @property
    def gid(self):
        return self.gids()[0]

    @property
    def is_attached(self):
        if self.application:
            if self.application.poll() is None:
                return True
        return False

    def attach(self):

        if not self._is_pulseaudio_user_process():
            self.disabled = True
            logger.info('Ignoring pulseaudio process ({pid})!'.format(
                pid=self.pid))
            return

        logger.info('Attaching application to pulseaudio ({pid})'.format(
            pid=self.pid))

        proc_env = self.env
        if not proc_env:
            logger.error(
                'Could not get the environment of pulseaudio ({pid}). '
                'Aborting.'.format(pid=self.pid))
            return

        missing_env = missing_env_vars(proc_env)
        if len(missing_env) > 0:
            logger.warning(
                'The following environment variables were not set: "{}". '
                'Starting as root may not work!'.format(','.join(missing_env)))

        try:
            self.application = (
                pulseaudio_dlna.utils.subprocess.GobjectSubprocess(
                    sys.argv,
                    uid=self.uid,
                    gid=self.gid,
                    env=self.compressed_env,
                    cwd=os.getcwd()))
        except OSError as e:
            self.application = None
            self.disabled = True
            logger.error(
                'Could not attach to pulseaudio ({pid}) - {msg}!'.format(
                    pid=self.pid, msg=e))

    def detach(self):
        app_pid = self.application.pid
        if app_pid:
            logger.info('Detaching application ({app_pid}) from '
                        'pulseaudio ({pid})'.format(
                            pid=self.pid, app_pid=app_pid))
            self._kill_process_tree(app_pid)
            self.application = None

    def _is_pulseaudio_user_process(self):
        return (self.uid >= self.UID_MIN and
                self._get_uid_name(self.uid) not in self.DISPLAY_MANAGERS)

    def _kill_process_tree(self, pid, timeout=3):
        try:
            p = psutil.Process(pid)
            for child in p.children():
                self._kill_process_tree(child.pid)
            p.send_signal(signal.SIGTERM)
            p.wait(timeout=timeout)
        except psutil.TimeoutExpired:
            logger.info(
                'Process {} did not exit, sending SIGKILL ...'.format(pid))
            p.kill()
        except psutil.NoSuchProcess:
            logger.info('Process {} has exited.'.format(pid))

    def _get_uid_name(self, uid):
        try:
            return pwd.getpwuid(uid).pw_name
        except KeyError:
            return None

    def _get_proc_env(self, pid):
        env = {}
        location = '/proc/{pid}/environ'.format(pid=pid)
        try:
            with open(location) as f:
                content = f.read()
            for line in content.split('\0'):
                try:
                    key, value = line.split('=', 1)
                    env[key] = value
                except ValueError:
                    pass
            return env
        except IOError:
            return None

    def __eq__(self, other):
        return self.pid == other.pid

    def __gt__(self, other):
        return self.pid > other.pid

    def __hash__(self):
        return self.pid


class PulseAudioFinder(object):
    @staticmethod
    def get_processes():
        processes = []
        try:
            for proc in psutil.process_iter():
                if proc.name() == 'pulseaudio':
                    proc.__class__ = PulseAudioProcess
                    if not hasattr(proc, 'application'):
                        proc.application = None
                    if not hasattr(proc, 'disabled'):
                        proc.disabled = False
                    processes.append(proc)
        except psutil.NoSuchProcess:
            pass
        return processes
