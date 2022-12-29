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

import re


def _get_header_map(header):
    header = re.findall(r"(?P<name>.*?):(?P<value>.*?)\n", header)
    header = {
        k.strip().lower(): v.strip() for k, v in list(dict(header).items())
    }
    return header


def _get_device_id(header):
    if 'usn' in header:
        match = re.search(
            "(uuid:.*?)::(.*)", header['usn'], re.IGNORECASE)
        if match:
            return match.group(1)
    return None
