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

import inspect

import encoders
import codecs

supported_encoders = []
supported_codecs = []


def load_encoders():
    for (name, _type) in inspect.getmembers(encoders):
        forbidden_members = [
            '__builtins__',
            '__doc__',
            '__file__',
            '__name__',
            '__package__',
            'unicode_literals'
        ]
        if name not in forbidden_members:
            try:
                encoder = _type()
            except:
                continue
            if name != 'BaseEncoder' and \
               isinstance(_type(), encoders.BaseEncoder):
                supported_encoders.append(encoder)
    supported_encoders.sort(reverse=True)


def load_codecs():
    for (name, _type) in inspect.getmembers(codecs):
        forbidden_members = [
            '__builtins__',
            '__doc__',
            '__file__',
            '__name__',
            '__package__',
            'unicode_literals'
        ]
        if name not in forbidden_members:
            try:
                codec = _type()
            except:
                continue
            if name != 'BaseCodec' and \
               isinstance(_type(), codecs.BaseCodec):
                supported_codecs.append(codec)
    supported_codecs.sort(reverse=True)

load_encoders()
load_codecs()
