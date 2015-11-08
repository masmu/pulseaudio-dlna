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
import pulseaudio_dlna.codecs

logger = logging.getLogger('pulseaudio_dlna.plugins.chromecast.renderer')


CHROMECAST_MODEL_NAMES = ['Eureka Dongle', 'Chromecast Audio']


class ChromecastRenderer(pulseaudio_dlna.plugins.renderer.BaseRenderer):

    def __init__(self, name, ip, udn, model_name, model_number, manufacturer):
        pulseaudio_dlna.plugins.renderer.BaseRenderer.__init__(
            self, udn, model_name, model_number, manufacturer)
        self.flavour = 'Chromecast'
        self.name = name
        self.ip = ip
        self.port = 8009
        self.state = self.IDLE
        self.codecs = []

    def activate(self, config):
        if config:
            self.set_rules_from_config(config)
        else:
            self.codecs = [
                pulseaudio_dlna.codecs.Mp3Codec(),
                pulseaudio_dlna.codecs.AacCodec(),
                pulseaudio_dlna.codecs.OggCodec(),
                pulseaudio_dlna.codecs.WavCodec(),
            ]

    def _get_media_player(self):
        try:
            return pycastv2.MediaPlayerController(self.ip, self.REQUEST_TIMEOUT)
        except socket.error as e:
            if e.errno == 111:
                logger.info(
                    'The chromecast refused the connection. Perhaps it '
                    'does not support the castv2 protocol.')
            else:
                traceback.print_exc()
            return None

    def play(self, url):
        cast = self._get_media_player()
        if cast is None:
            logger.error('No device was found!')
            return 500
        try:
            cast.load(url, self.codec.mime_type)
            self.state = self.PLAYING
            return 200
        except pycastv2.ChannelClosedException:
            logger.info('Connection was closed. I guess another '
                        'client is attached to it.')
            return 423
        except pycastv2.TimeoutException:
            logger.error('PLAY command - Could no connect to "{device}". '
                         'Connection timeout.'.format(device=self.label))
            return 408
        finally:
            cast.cleanup()

    def stop(self):
        cast = self._get_media_player()
        if cast is None:
            logger.error('No device was found!')
            return 500
        try:
            self.state = self.IDLE
            cast.disconnect_application()
            return 200
        except pycastv2.ChannelClosedException:
            logger.info('Connection was closed. I guess another '
                        'client is attached to it.')
            return 423
        except pycastv2.TimeoutException:
            logger.error('STOP command - Could no connect to "{device}". '
                         'Connection timeout.'.format(device=self.label))
            return 408
        finally:
            cast.cleanup()

    def pause(self):
        raise NotImplementedError()


class CoinedChromecastRenderer(
        pulseaudio_dlna.plugins.renderer.CoinedBaseRendererMixin, ChromecastRenderer):

    def play(self, url=None, codec=None):
        try:
            stream_url = url or self.get_stream_url()
            return ChromecastRenderer.play(self, stream_url)
        except pulseaudio_dlna.plugins.renderer.NoSuitableEncoderFoundException:
            return 500


class ChromecastRendererFactory(object):

    @classmethod
    def from_url(self, url, type_=ChromecastRenderer):
        try:
            response = requests.get(url)
            logger.debug('Response from chromecast device ({url})\n'
                         '{response}'.format(url=url, response=response.text))
        except requests.exceptions.ConnectionError:
            logger.info(
                'Could no connect to {url}. '
                'Connection refused.'.format(url=url))
            return None
        soup = BeautifulSoup.BeautifulSoup(
            response.content.decode('utf-8'),
            convertEntities=BeautifulSoup.BeautifulSoup.HTML_ENTITIES)
        url_object = urlparse.urlparse(url)
        ip, port = url_object.netloc.split(':')
        try:
            model_name = soup.root.device.modelname.text
            if model_name.strip() not in CHROMECAST_MODEL_NAMES:
                logger.info(
                    'The Chromecast seems not to be an original Chromecast! '
                    'Model name: "{model_name}" Skipping device ...'.format(
                        model_name=model_name))
                return None
            cast_device = type_(
                soup.root.device.friendlyname.text,
                ip,
                soup.root.device.udn.text,
                soup.root.device.modelname.text,
                None,
                soup.root.device.manufacturer.text)
            return cast_device
        except AttributeError:
            logger.error(
                'No valid XML returned from {url}.'.format(url=url))
            return None

    @classmethod
    def from_header(self, header, type_=ChromecastRenderer):
        if header.get('location', None):
            return self.from_url(header['location'], type_)
