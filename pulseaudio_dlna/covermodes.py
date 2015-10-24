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

import sys
import inspect
import socket
import logging

logger = logging.getLogger('pulseaudio_dlna.covermodes')


MODES = {}


class BaseCoverMode(object):

    IDENTIFIER = None

    def __init__(self):
        pass

    def get(self, bridge):
        return None, None, None


class ApplicationCoverMode(BaseCoverMode):

    IDENTIFIER = 'application'

    def get(self, bridge):
        artist = 'Liveaudio on {}'.format(socket.gethostname())
        title = ', '.join(bridge.sink.stream_client_names)
        thumb = bridge.device.get_image_url('application.png')
        return artist, title, thumb


def load_modes():
    if len(MODES) == 0:
        logger.info('Loaded modes:')
        for name, _type in inspect.getmembers(sys.modules[__name__]):
            if inspect.isclass(_type) and issubclass(_type, BaseCoverMode):
                if _type is not BaseCoverMode:
                    logger.info('  {} = {}'.format(_type.IDENTIFIER, _type))
                    MODES[_type.IDENTIFIER] = _type
    return None

load_modes()
