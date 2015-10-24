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
from __future__ import with_statement

import logging

logger = logging.getLogger('pulseaudio_dlna.images')


class UnknownImageExtension(Exception):
    pass


class ImageNotAccessible(Exception):
    pass


def get_icon_by_name(name, size=256):
    try:
        import gtk
    except:
        logger.error(
            'Unable to retrieve system icons. You need to install: python-gtk2')
        return None
    icon_theme = gtk.icon_theme_get_default()
    icon = icon_theme.lookup_icon(name, size, 0)
    if icon:
        file_path = icon.get_filename()
        _type = get_type_by_filename(file_path)
        return _type(file_path)
    return None


def get_type_by_filename(path):
    if path.endswith('.png'):
        return PngImage
    elif path.endswith('.jpg'):
        return JpgImage
    logger.debug('Unknown image type: "{}"'.format(path))
    raise UnknownImageExtension()


class BaseImage(object):
    def __init__(self, path, cached=True):
        self.path = path
        self.content_type = None
        self.cached = cached

        if self.cached:
            self._read_data()

    def _read_data(self):
        try:
            with open(self.path) as h:
                self._data = h.read()
        except EnvironmentError:
            raise ImageNotAccessible()

    @property
    def data(self):
        if self.cached:
            return self._data
        else:
            return self._read_data()


class PngImage(BaseImage):
    def __init__(self, path, cached=True):
        BaseImage.__init__(self, path, cached)
        self.content_type = 'image/png'


class JpgImage(BaseImage):
    def __init__(self, path, cached=True):
        BaseImage.__init__(self, path, cached)
        self.content_type = 'image/jpeg'
