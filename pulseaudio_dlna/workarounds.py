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
import requests
import urlparse
import BeautifulSoup


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
            logger.debug('Running workaround "{}".'.format(method_name))
            method(*args, **kwargs)


class YamahaWorkaround(BaseWorkaround):

    REQUEST_TIMEOUT = 5
    ENCODING = 'utf-8'

    XML_PUT = ('<YAMAHA_AV cmd="PUT"><{zone}><{category}><{key}>{value}'
               '</{key}></{category}></{zone}></YAMAHA_AV>')

    def __init__(self, xml):
        BaseWorkaround.__init__(self)
        self.control_url = None
        self._parse_xml(xml)

    def before_play(self):
        if self.control_url:
            self.set_source('PC')
        else:
            logger.error(
                'Not sending Yamaha AVRC command. No control url found!')

    def set_source(self, mode='PC'):
        self._put('Main Zone', 'Input', 'Input_Sel', mode)

    def _parse_xml(self, xml):
        soup = BeautifulSoup.BeautifulSoup(xml)
        for device in soup.root.findAll('yamaha:x_device'):
            url_base = device.find('yamaha:x_urlbase')
            control_path = device.find('yamaha:x_controlurl')
            if url_base and control_path:
                self.control_url = urlparse.urljoin(
                    url_base.text, control_path.text)

    def _put(self, zone, category, key, value):
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(
                    encoding=self.ENCODING),
        }
        data = self.XML_PUT.format(
            zone=zone, category=category, key=key, value=value)
        try:
            logger.debug(
                'Yamaha AVRC command - POST request: {request}'.format(
                    request=data))
            response = requests.post(
                self.control_url, data.encode(self.ENCODING),
                headers=headers, timeout=self.REQUEST_TIMEOUT)
            logger.debug(
                'Yamaha AVRC command - POST response: {response}'.format(
                    response=response.text))
        except requests.exceptions.Timeout:
            logger.error(
                'Yamaha AVRC {category} command - Could no connect to {url}. '
                'Connection timeout.'.format(
                    url=self.control_url, category=category))
