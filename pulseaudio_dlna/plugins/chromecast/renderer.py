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

import requests
import logging
import urllib.parse
import traceback
import lxml

import pulseaudio_dlna.plugins.renderer
import pulseaudio_dlna.rules
import pulseaudio_dlna.codecs

from pychromecast import Chromecast
from pychromecast.dial import DeviceStatus, CAST_TYPES, CAST_TYPE_CHROMECAST
from pychromecast.error import PyChromecastError

logger = logging.getLogger('pulseaudio_dlna.plugins.chromecast.renderer')


class ChromecastRenderer(pulseaudio_dlna.plugins.renderer.BaseRenderer):

    def __init__(self, chromecast, model_number=None, model_description=None):
        pulseaudio_dlna.plugins.renderer.BaseRenderer.__init__(
            self,
            udn=chromecast.uuid,
            flavour='Chromecast',
            name=chromecast.name,
            ip=chromecast.host,
            port=chromecast.port,
            model_name=chromecast.model_name,
            model_number=model_number,
            model_description=model_description,
            manufacturer=chromecast.device.manufacturer
        )
        self.chromecast = chromecast

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
            self.apply_device_rules()
            self.prioritize_codecs()

    def play(self, url=None, codec=None, artist=None, title=None, thumb=None):
        self._before_play()
        url = url or self.get_stream_url()
        try:
            # TODO: artist missing
            self.chromecast.play_media(
                url, mime_type=self.codec.mime_type, title=title, thumb=thumb)
            self.state = self.STATE_PLAYING
            return 200, None
        except PyChromecastError as e:
            return 500, str(e)
        except (pulseaudio_dlna.plugins.renderer.NoEncoderFoundException,
                pulseaudio_dlna.plugins.renderer.NoSuitableHostFoundException) as e:
            return 500, e
        except Exception:
            traceback.print_exc()
            return 500, 'Unknown exception.'
        finally:
            self._after_play()

    def stop(self):
        self._before_stop()
        try:
            self.state = self.STATE_STOPPED
            self.chromecast.stop()
            self.chromecast.disconnect()
            return 200, None
        except PyChromecastError as e:
            return 500, e
        except Exception:
            traceback.print_exc()
            return 500, 'Unknown exception.'
        finally:
            self._after_stop()

    def pause(self):
        raise NotImplementedError()


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
    def from_url(cls, url):
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
        return cls.from_xml(url, response.content)

    @classmethod
    def from_xml(cls, url, xml):
        url_object = urllib.parse.urlparse(url)
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

                return cls.from_properties(
                    name=str(device_friendlyname.text),
                    ip=str(ip),
                    port=None,
                    udn=str(device_udn.text),
                    model_name=str(device_modelname.text),
                    model_number=None,
                    model_description=None,
                    manufacturer=str(device_manufacturer.text),
                )
        except Exception as e:
            logger.error('No valid XML returned from {url}.'.format(url=url))
            return None

    @classmethod
    def from_header(cls, header):
        if header.get('location', None):
            return cls.from_url(header['location'])

    @classmethod
    def from_properties(
            cls, name, ip, port, udn, model_name, model_number,
            model_description, manufacturer):
        cast_type = CAST_TYPES.get(model_name.lower(),
                                   CAST_TYPE_CHROMECAST)
        device = DeviceStatus(
            friendly_name=name, model_name=model_name,
            manufacturer=manufacturer, uuid=udn, cast_type=cast_type,
        )
        chromecast = Chromecast(host=ip, port=port or 8009, device=device)
        return ChromecastRenderer(
            chromecast=chromecast,
            model_number=model_number,
            model_description=model_description)
