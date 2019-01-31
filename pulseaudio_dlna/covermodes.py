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

import sys
import inspect
import socket
import platform
import logging

logger = logging.getLogger('pulseaudio_dlna.covermodes')


MODES = {}


class UnknownCoverModeException(Exception):
    def __init__(self, cover_mode):
        Exception.__init__(
            self,
            'You specified an unknown cover mode "{}"!'.format(cover_mode)
        )


def validate(cover_mode):
    if cover_mode not in MODES:
        raise UnknownCoverModeException(cover_mode)


class BaseCoverMode(object):

    IDENTIFIER = None

    def __init__(self):
        self.bridge = None

    @property
    def artist(self):
        return 'Liveaudio on {}'.format(socket.gethostname())

    @property
    def title(self):
        return ', '.join(self.bridge.sink.stream_client_names)

    @property
    def thumb(self):
        return None

    def get(self, bridge):
        try:
            self.bridge = bridge
            return self.artist, self.title, self.thumb
        finally:
            self.bridge = None


class DisabledCoverMode(BaseCoverMode):

    IDENTIFIER = 'disabled'


class DefaultCoverMode(BaseCoverMode):

    IDENTIFIER = 'default'

    @property
    def thumb(self):
        try:
            return self.bridge.device.get_image_url('default.png')
        except Exception:
            return None


class DistributionCoverMode(BaseCoverMode):

    IDENTIFIER = 'distribution'

    @property
    def thumb(self):
        dist_name, dist_ver, dist_arch = platform.linux_distribution()
        logger.debug(dist_name)
        if dist_name == 'Ubuntu':
            dist_icon = 'ubuntu'
        elif dist_name == 'debian':
            dist_icon = 'debian'
        elif dist_name == 'fedora':
            dist_icon = 'fedora'
        elif dist_name == 'LinuxMint':
            dist_icon = 'linuxmint'
        elif dist_name == 'openSUSE' or dist_name == 'SuSE':
            dist_icon = 'opensuse'
        elif dist_name == 'gentoo':
            dist_icon = 'gentoo'
        else:
            dist_icon = 'unknown'
        try:
            return self.bridge.device.get_image_url(
                'distribution-{}.png'.format(dist_icon))
        except Exception:
            return None


class ApplicationCoverMode(BaseCoverMode):

    IDENTIFIER = 'application'

    @property
    def thumb(self):
        try:
            return self.bridge.device.get_sys_icon_url(
                self.bridge.sink.primary_application_name)
        except Exception:
            return None


def load_modes():
    if len(MODES) == 0:
        for name, _type in inspect.getmembers(sys.modules[__name__]):
            if inspect.isclass(_type) and issubclass(_type, BaseCoverMode):
                if _type is not BaseCoverMode:
                    MODES[_type.IDENTIFIER] = _type
    return None


load_modes()
