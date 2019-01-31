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

import os

GIT_DIRECTORY = '../../.git/'


def get_head_version():

    def _get_first_line(path):
        try:
            with open(path) as f:
                content = f.readlines()
                return content[0]
        except EnvironmentError:
            return None

    module_path = os.path.dirname(os.path.abspath(__file__))
    head_path = os.path.join(module_path, GIT_DIRECTORY, 'HEAD')
    line = _get_first_line(head_path)

    if not line:
        return None, None
    elif line.startswith('ref: '):
        prefix, ref_path = [s.strip() for s in line.split('ref: ')]
        branch = os.path.basename(ref_path)
        ref_path = os.path.join(module_path, GIT_DIRECTORY, ref_path)
        return branch, (_get_first_line(ref_path) or 'unknown').strip()
    else:
        return 'detached-head', line.strip()
