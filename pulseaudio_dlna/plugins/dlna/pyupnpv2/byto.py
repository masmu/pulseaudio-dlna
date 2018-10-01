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

"""A module which runs things without importing unicode_literals

Sometimes you want python3s builtin functions just to run on raw bytes. Since
the unicode_literals module changes that behavior for many string manipulations
this module is a workarounds for not using future.utils.bytes_to_native_str
method.

"""

import re


def repair_xml(bytes):

    def strip_namespaces(match):
        return 'xmlns{prefix}="{content}"'.format(
            prefix=match.group(1) if match.group(1) else '',
            content=match.group(2).strip(),
        )

    bytes = re.sub(
        r'xmlns(:.*?)?="(.*?)"', strip_namespaces, bytes,
        flags=re.IGNORECASE)

    return bytes
