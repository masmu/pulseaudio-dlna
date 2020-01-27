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

import functools


class BasePlugin(object):
    def __init__(self):
        self.st_header = None
        self.holder = None

    def lookup(self, locations, data):
        raise NotImplementedError()

    def discover(self, ttl=None, host=None):
        raise NotImplementedError()

    @staticmethod
    def add_device_after(f, *args):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            device = f(*args, **kwargs)
            self = args[0]
            if self.holder:
                self.holder.add_device(device)
            return device
        return wrapper

    @staticmethod
    def remove_device_after(f, *args):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            device_id = f(*args, **kwargs)
            self = args[0]
            if self.holder:
                self.holder.remove_device(device_id)
            return device_id
        return wrapper
