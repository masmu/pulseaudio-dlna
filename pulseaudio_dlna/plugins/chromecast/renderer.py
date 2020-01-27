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
import pychromecast

import pulseaudio_dlna.plugins.renderer
import pulseaudio_dlna.rules
import pulseaudio_dlna.codecs


logger = logging.getLogger('pulseaudio_dlna.plugins.chromecast.renderer')


class ChromecastRenderer(pulseaudio_dlna.plugins.renderer.BaseRenderer):

    def __init__(
            self, name, ip, port, udn, model_name, model_number,
            model_description, manufacturer):
        pulseaudio_dlna.plugins.renderer.BaseRenderer.__init__(
            self,
            udn=udn,
            flavour='Chromecast',
            name=name,
            ip=ip,
            port=port or 8009,
            model_name=model_name,
            model_number=model_number,
            model_description=model_description,
            manufacturer=manufacturer
        )

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

    def _create_pychromecast(self):
        chromecast = pychromecast._get_chromecast_from_host(
            (self.ip, self.port, self.udn, self.model_name, self.name))
        return chromecast

    def play(self, url=None, codec=None, artist=None, title=None, thumb=None):
        self._before_play()
        url = url or self.get_stream_url()
        try:
            chromecast = self._create_pychromecast()
            chromecast.media_controller.play_media(
                url,
                content_type=self.codec.mime_type,
                title=title,
                thumb=thumb,
                stream_type=pychromecast.controllers.media.STREAM_TYPE_LIVE,
                autoplay=True,
            )
            self.state = self.STATE_PLAYING
            return 200, None
        except pychromecast.error.PyChromecastError as e:
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
            chromecast = self._create_pychromecast()
            chromecast.quit_app()
            return 200, None
        except pychromecast.error.PyChromecastError as e:
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
        'urn:dial-multiscreen-org:device:dial:',
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

                valid_notification_type = False
                for notification_type in cls.NOTIFICATION_TYPES:
                    if device_type.text.startswith(notification_type):
                        valid_notification_type = True
                        break

                if valid_notification_type:
                    return ChromecastRenderer(
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
            traceback.print_exc()
            logger.error('No valid XML returned from {url}.'.format(url=url))
            return None

    @classmethod
    def from_header(cls, header):
        if header.get('location', None):
            return cls.from_url(header['location'])

    @classmethod
    def from_pychromecast(self, pychromecast):
        return ChromecastRenderer(
            name=pychromecast.name,
            ip=pychromecast.host,
            port=pychromecast.port,
            udn='uuid:{}'.format(pychromecast.uuid),
            model_name=pychromecast.model_name,
            model_number=None,
            model_description=None,
            manufacturer=pychromecast.device.manufacturer,
        )
