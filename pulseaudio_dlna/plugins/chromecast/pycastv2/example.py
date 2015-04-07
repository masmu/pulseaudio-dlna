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

import logging
import __init__ as pycastv2

logging.basicConfig(level=logging.DEBUG)

mc = pycastv2.MediaPlayerController('192.168.10.39')
try:
    mc.load('http://192.168.1.2:8080/stream.mp3', 'audio/mpeg')
    mc.wait(10)
    mc.close_application()
    # mc.stop()
finally:
    mc.cleanup()
