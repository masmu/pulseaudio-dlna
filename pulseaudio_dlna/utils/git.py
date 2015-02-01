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

import commands


def describe_tags():
    status_code, result = commands.getstatusoutput('git describe --tags')
    if status_code == 0:
        return result
    return 'unknown'


def short_revision_hash():
    status_code, result = commands.getstatusoutput('git rev-parse --short HEAD')
    if status_code == 0:
        return result
    return 'unknown'
