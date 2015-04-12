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

import requests
import logging
import urlparse
import socket
import traceback
import BeautifulSoup

import pycastv2
import pulseaudio_dlna.plugins.renderer


class ChromecastRenderer(pulseaudio_dlna.plugins.renderer.BaseRenderer):

    def __init__(self, name, ip):
        pulseaudio_dlna.plugins.renderer.BaseRenderer.__init__(self)
        self.flavour = 'Chromecast'
        self.name = name
        self.ip = ip
        self.port = 8009
        self.state = self.IDLE
        self.protocols = [
            'audio/mp3',
            'audio/mp4',
            'audio/ogg',
            'audio/wav',
        ]

    def _get_media_player(self):
        try:
            return pycastv2.MediaPlayerController(self.ip)
        except socket.error as e:
            if e.errno == 111:
                logging.info(
                    'The chromecast refused the connection. Perhaps it '
                    'does not support the castv2 protocol.')
            else:
                traceback.print_exc()
            return None

    def play(self, url):
        cast = self._get_media_player()
        if cast is None:
            return 500
        try:
            if cast.load(url, self.encoder.mime_type) is True:
                self.state = self.PLAYING
                return 200
            return 500
        finally:
            cast.cleanup()

    def stop(self):
        cast = self._get_media_player()
        if cast is None:
            return 500
        try:
            self.state = self.IDLE
            if cast.disconnect_application() is True:
                return 200
            return 500
        finally:
            cast.cleanup()

    def pause(self):
        raise NotImplementedError()


class CoinedChromecastRenderer(
        pulseaudio_dlna.plugins.renderer.CoinedBaseRendererMixin, ChromecastRenderer):

    def play(self):
        try:
            return ChromecastRenderer.play(self, self.get_stream_url())
        except pulseaudio_dlna.plugins.renderer.NoSuitableEncoderFoundException:
            return 500


class ChromecastRendererFactory(object):

    @classmethod
    def from_url(self, url, type_=ChromecastRenderer):
        try:
            response = requests.get(url)
            logging.debug('Response from chromecast device ({url})\n'
                          '{response}'.format(url=url, response=response.text))
        except requests.exceptions.ConnectionError:
            logging.info(
                'Could no connect to {url}. '
                'Connection refused.'.format(url=url))
            return None
        soup = BeautifulSoup.BeautifulSoup(response.content)
        url_object = urlparse.urlparse(url)
        ip, port = url_object.netloc.split(':')
        try:
            cast_device = type_(
                soup.root.device.friendlyname.text,
                ip)
            return cast_device
        except AttributeError:
            logging.info(
                'No valid XML returned from {url}.'.format(url=url))
            return None

    @classmethod
    def from_header(self, header, type_=ChromecastRenderer):
        if header['location']:
            return self.from_url(header['location'], type_)
