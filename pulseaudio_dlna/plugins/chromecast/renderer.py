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
import lxml

import pycastv2
import pulseaudio_dlna.plugins.renderer
import pulseaudio_dlna.codecs

logger = logging.getLogger('pulseaudio_dlna.plugins.chromecast.renderer')


class ChromecastRenderer(pulseaudio_dlna.plugins.renderer.BaseRenderer):

    def __init__(
            self, name, ip, port, udn, model_name, model_number, manufacturer):
        pulseaudio_dlna.plugins.renderer.BaseRenderer.__init__(
            self, udn, model_name, model_number, manufacturer)
        self.flavour = 'Chromecast'
        self.name = name
        self.ip = ip
        self.port = port or 8009
        self.state = self.IDLE
        self.codecs = []

    def activate(self, config):
        if config:
            self.set_rules_from_config(config)
        else:
            self.codecs = [
                pulseaudio_dlna.codecs.Mp3Codec(),
                pulseaudio_dlna.codecs.FlacCodec(),
                pulseaudio_dlna.codecs.WavCodec(),
                pulseaudio_dlna.codecs.OggCodec(),
                pulseaudio_dlna.codecs.AacCodec(),
            ]
            if pulseaudio_dlna.plugins.renderer.DISABLE_MIMETYPE_CHECK:
                for codec in pulseaudio_dlna.codecs.enabled_codecs():
                    if codec not in self.codecs:
                        self.codecs.append(codec)
                self.prioritize_codecs()

    def play(self, url, artist=None, title=None, thumb=None):
        self._before_play()
        try:
            cast = pycastv2.MediaPlayerController(
                self.ip, self.port, self.REQUEST_TIMEOUT)
            cast.load(
                url,
                mime_type=self.codec.mime_type,
                artist=artist,
                title=title,
                thumb=thumb)
            self.state = self.PLAYING
            return 200, None
        except pycastv2.LaunchErrorException:
            message = 'The media player could not be launched. ' \
                      'Maybe the chromecast is still closing a ' \
                      'running player instance. Try again in 30 seconds.'
            return 503, message
        except pycastv2.ChannelClosedException:
            message = 'Connection was closed. I guess another ' \
                      'client is attached to it.'
            return 423, message
        except pycastv2.TimeoutException:
            message = 'PLAY command - Could no connect to "{device}". ' \
                      'Connection timeout.'.format(device=self.label)
            return 408, message
        except socket.error as e:
            if e.errno == 111:
                message = 'The chromecast refused the connection. ' \
                          'Perhaps it does not support the castv2 ' \
                          'protocol.'
                return 403, message
            else:
                traceback.print_exc()
            return 500, None
        finally:
            self._after_play()
            cast.cleanup()

    def stop(self):
        self._before_stop()
        try:
            cast = pycastv2.MediaPlayerController(
                self.ip, self.port, self.REQUEST_TIMEOUT)
            self.state = self.IDLE
            cast.disconnect_application()
            return 200, None
        except pycastv2.ChannelClosedException:
            message = 'Connection was closed. I guess another ' \
                      'client is attached to it.'
            return 423, message
        except pycastv2.TimeoutException:
            message = 'STOP command - Could no connect to "{device}". ' \
                      'Connection timeout.'.format(device=self.label)
            return 408, message
        except socket.error as e:
            if e.errno == 111:
                message = 'The chromecast refused the connection. ' \
                          'Perhaps it does not support the castv2 ' \
                          'protocol.'
                return 403, message
            else:
                traceback.print_exc()
            return 500, None
        finally:
            self._after_stop()
            cast.cleanup()

    def pause(self):
        raise NotImplementedError()


class CoinedChromecastRenderer(
        pulseaudio_dlna.plugins.renderer.CoinedBaseRendererMixin,
        ChromecastRenderer):

    def play(self, url=None, codec=None, artist=None, title=None, thumb=None):
        try:
            stream_url = url or self.get_stream_url()
            return ChromecastRenderer.play(
                self, stream_url, artist=artist, title=title, thumb=thumb)
        except (pulseaudio_dlna.plugins.renderer.NoEncoderFoundException,
                pulseaudio_dlna.plugins.renderer.NoSuitableHostFoundException) as e:
            return 500, e


class ChromecastRendererFactory(object):

    NOTIFICATION_TYPES = [
        'urn:dial-multiscreen-org:device:dial:1',
    ]

    CHROMECAST_MODELS = [
        'Eureka Dongle',
        'Chromecast Audio',
        'Nexus Player',
        'Freebox Player Mini',
    ]

    @classmethod
    def from_url(cls, url, type_=ChromecastRenderer):
        try:
            response = requests.get(url, timeout=5)
            logger.debug('Response from chromecast device ({url})\n'
                         '{response}'.format(url=url, response=response.text))
        except requests.exceptions.Timeout:
            logger.warning(
                'Could no connect to {url}. '
                'Connection timeout.'.format(url=url))
            return None
        except requests.exceptions.ConnectionError:
            logger.warning(
                'Could no connect to {url}. '
                'Connection refused.'.format(url=url))
            return None
        return cls.from_xml(url, response.content, type_)

    @classmethod
    def from_xml(cls, url, xml, type_=ChromecastRenderer):
        url_object = urlparse.urlparse(url)
        ip, port = url_object.netloc.split(':')
        try:
            xml_root = lxml.etree.fromstring(xml)
            for device in xml_root.findall('.//{*}device'):
                device_type = device.find('{*}deviceType')
                device_friendlyname = device.find('{*}friendlyName')
                device_udn = device.find('{*}UDN')
                device_modelname = device.find('{*}modelName')
                device_manufacturer = device.find('{*}manufacturer')

                if device_type.text not in cls.NOTIFICATION_TYPES:
                    continue

                if device_modelname.text.strip() not in cls.CHROMECAST_MODELS:
                    logger.info(
                        'The Chromecast seems not to be an original one. '
                        'Model name: "{}" Skipping device ...'.format(
                            device_modelname.text))
                    return None

                cast_device = type_(
                    unicode(device_friendlyname.text),
                    unicode(ip),
                    None,
                    unicode(device_udn.text),
                    unicode(device_modelname.text),
                    None,
                    unicode(device_manufacturer.text),
                )
                return cast_device
        except:
            logger.error('No valid XML returned from {url}.'.format(url=url))
            return None

    @classmethod
    def from_header(cls, header, type_=ChromecastRenderer):
        if header.get('location', None):
            return cls.from_url(header['location'], type_)

    @classmethod
    def from_mdns_info(cls, info, type_=ChromecastRenderer):

        def _bytes2string(bytes):
            ip = []
            for b in bytes:
                subnet = int(b.encode('hex'), 16)
                ip.append(str(subnet))
            return '.'.join(ip)

        def _get_device_info(info):
            try:
                return {
                    'udn': '{}:{}'.format('uuid', info.properties['id']),
                    'type': info.properties['md'].decode('utf-8'),
                    'name': info.properties['fn'].decode('utf-8'),
                    'ip': _bytes2string(info.address),
                    'port': int(info.port),
                }
            except (KeyError, AttributeError, TypeError):
                return None

        device_info = _get_device_info(info)
        if device_info:
            return type_(
                name=device_info['name'],
                ip=device_info['ip'],
                port=device_info['port'],
                udn=device_info['udn'],
                model_name=device_info['type'],
                model_number=None,
                manufacturer='Google Inc.'
            )
        return None
