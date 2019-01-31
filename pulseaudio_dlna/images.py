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


import tempfile
import logging
import gi

logger = logging.getLogger('pulseaudio_dlna.images')


class UnknownImageExtension(Exception):
    def __init__(self, path):
        Exception.__init__(
            self,
            'The file "{}" has an unsupported file extension!'.format(path)
        )


class ImageNotAccessible(Exception):
    def __init__(self, path):
        Exception.__init__(
            self,
            'The file "{}" is not accessible!'.format(path)
        )


class IconNotFound(Exception):
    def __init__(self, icon_name):
        Exception.__init__(
            self,
            'The icon "{}" could not be found!'.format(icon_name)
        )


class MissingDependencies(Exception):
    def __init__(self, message, dependencies):
        Exception.__init__(
            self,
            '{} - Could not load one of following modules "{}"!'.format(
                message, ','.join(dependencies))
        )


def get_icon_by_name(name, size=256):
    try:
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
    except Exception:
        raise MissingDependencies(
            'Unable to lookup system icons!',
            ['gir1.2-gtk-3.0']
        )

    icon_theme = Gtk.IconTheme.get_default()
    icon = icon_theme.lookup_icon(name, size, 0)
    if icon:
        file_path = icon.get_filename()
        _type = get_type_by_filepath(file_path)
        return _type(file_path)
    else:
        raise IconNotFound(name)


def get_type_by_filepath(path):
    if path.endswith('.png'):
        return PngImage
    elif path.endswith('.jpg'):
        return JpgImage
    elif path.endswith('.svg'):
        return SvgPngImage
    raise UnknownImageExtension(path)


class BaseImage(object):
    def __init__(self, path, cached=True):
        self.path = path
        self.content_type = None
        self.cached = cached

        if self.cached:
            self._read_data()

    def _read_data(self):
        try:
            with open(self.path, 'rb') as h:
                self._data = h.read()
        except EnvironmentError:
            raise ImageNotAccessible(self.path)

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


class SvgPngImage(BaseImage):
    def __init__(self, path, cached=True, size=256):
        try:
            gi.require_version('Rsvg', '2.0')
            from gi.repository import Rsvg
        except Exception:
            raise MissingDependencies(
                'Unable to convert SVG image to PNG!', ['gir1.2-rsvg-2.0']
            )
        try:
            import cairo
        except Exception:
            raise MissingDependencies(
                'Unable to convert SVG image to PNG!', ['cairo']
            )

        tmp_file = tempfile.NamedTemporaryFile()
        image_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
        rsvg_handle = Rsvg.Handle.new_from_file(path)

        context = cairo.Context(image_surface)
        context.scale(
            float(size) / rsvg_handle.props.height,
            float(size) / rsvg_handle.props.width
        )
        rsvg_handle.render_cairo(context)
        image_surface.write_to_png(tmp_file.name)

        BaseImage.__init__(self, tmp_file.name, cached=True)


class JpgImage(BaseImage):
    def __init__(self, path, cached=True):
        BaseImage.__init__(self, path, cached)
        self.content_type = 'image/jpeg'
