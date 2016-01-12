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

logger = logging.getLogger('pulseaudio_dlna.workarounds')


class BaseWorkaround(object):
    """
    Define functions which are called at specific situations during the
    application.

    Those may be:
        - before_play
        - after_play
        - before_stop
        - after_stop

    This may be extended in the future.
    """

    def __init__(self):
        pass

    def run(self, method_name, *args, **kwargs):
        method = getattr(self, method_name, None)
        if method and callable(method):
            logger.info('Running workaround "{}".'.format(method_name))
            method(*args, **kwargs)


class YamahaWorkaround(BaseWorkaround):

    REQUEST_TIMEOUT = 5
    ENCODING = 'utf-8'

    def __init__(self, xml):
        BaseWorkaround.__init__(self)
        self.control_url = None
        self._parse_xml(xml)

    def _parse_xml(self, xml):
        pass

    def before_play(self):
        pass
