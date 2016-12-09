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

import pulseaudio_dlna.pulseaudio
import pulseaudio_dlna.encoders
import pulseaudio_dlna.workarounds
import pulseaudio_dlna.codecs
import pulseaudio_dlna.rules
import pulseaudio_dlna.plugins.renderer
import upnp

logger = logging.getLogger('pulseaudio_dlna.plugins.dlna.renderer')


class DLNAMediaRenderer(pulseaudio_dlna.plugins.renderer.BaseRenderer):

    def __init__(self, upnp_device):
        pulseaudio_dlna.plugins.renderer.BaseRenderer.__init__(
            self,
            udn=upnp_device.udn,
            flavour='DLNA',
            name=upnp_device.name,
            ip=upnp_device.ip,
            port=upnp_device.port,
            model_name=upnp_device.model_name,
            model_number=upnp_device.model_number,
            model_description=upnp_device.model_description,
            manufacturer=upnp_device.manufacturer
        )
        self.upnp_device = upnp_device
        self.upnp_device.timeout = self.REQUEST_TIMEOUT

    @property
    def content_features(self):
        return self.upnp_device.content_features

    @property
    def state(self):
        if self.upnp_device.state == upnp.UPNP_STATE_PLAYING:
            return self.PLAYING
        elif self.upnp_device.state == upnp.UPNP_STATE_STOPPED:
            return self.IDLE
        elif self.upnp_device.state is None:
            return self.IDLE
        else:
            logger.warning('Could not get an appropriate state value!')

    @state.setter
    def state(self, value):
        if value == self.PLAYING:
            self.upnp_device.state = upnp.UPNP_STATE_PLAYING
        elif value == self.IDLE:
            self.upnp_device.state = upnp.UPNP_STATE_STOPPED
        else:
            logger.warning('Could not set an appropriate state value!')

    def activate(self, config):
        if config:
            self.set_rules_from_config(config)
        else:
            self.codecs = []
            mime_types = self.upnp_device._get_protocol_info()
            if mime_types:
                for mime_type in mime_types:
                    self.add_mime_type(mime_type)
            self.apply_device_fixes()
            self.apply_device_rules()
            self.prioritize_codecs()

    def validate(self):
        if self.upnp_device.service_transport is None:
            logger.info(
                'The device "{}" does not specify a service transport url. '
                'Device skipped!'.format(self.label))
            return False
        if self.upnp_device.service_connection is None:
            logger.info(
                'The device "{}" does not specify a service connection url. '
                'Device skipped!'.format(self.label))
            return False
        if self.upnp_device.service_rendering is None:
            logger.info(
                'The device "{}" does not specify a service rendering url. '
                'Device skipped!'.format(self.label))
            return False
        return True

    def play(self, url=None, codec=None, artist=None, title=None, thumb=None):
        self._before_play()
        try:
            stream_url = url or self.get_stream_url()
            return_code, message = self.upnp_device.register(
                stream_url, codec, artist=artist, title=title, thumb=thumb)
            if return_code == 200:
                if pulseaudio_dlna.rules.DISABLE_PLAY_COMMAND in self.rules:
                    logger.info(
                        'Disabled play command. Device should be playing ...')
                    return return_code, message
                elif self.upnp_device._update_current_state():
                    if self.upnp_device.state == upnp.UPNP_STATE_STOPPED:
                        logger.info(
                            'Device state is stopped. Sending play command.')
                        return self.upnp_device.play()
                    elif self.upnp_device.state == upnp.UPNP_STATE_PLAYING:
                        logger.info(
                            'Device state is playing. No need '
                            'to send play command.')
                        return return_code, message
                else:
                    logger.warning(
                        'Updating device state unsuccessful! '
                        'Sending play command.')
                    return self.upnp_device.play()
            else:
                logger.error('"{}" registering failed!'.format(self.name))
                return return_code, None
        except requests.exceptions.ConnectionError:
            return 403, 'The device refused the connection!'
        except (pulseaudio_dlna.plugins.renderer.NoEncoderFoundException,
                pulseaudio_dlna.plugins.renderer.NoSuitableHostFoundException) as e:
            return 500, e
        finally:
            self._after_play()

    def stop(self):
        self._before_stop()
        return_code, message = self.upnp_device.stop()
        self._after_stop()
        return return_code, message

    def register(
            self, stream_url, codec=None, artist=None, title=None, thumb=None):
        self._before_register()
        codec = codec or self.codec
        return_code, message = self.upnp_device.register(
            stream_url, codec.mime_type, artist, title, thumb)
        self._after_register()
        return return_code, message


class DLNAMediaRendererFactory(object):

    @classmethod
    def from_url(cls, url):
        upnp_device = upnp.UpnpMediaRendererFactory.from_url(url)
        if upnp_device:
            return DLNAMediaRenderer(upnp_device)
        return None

    @classmethod
    def from_xml(cls, url, xml):
        upnp_device = upnp.UpnpMediaRendererFactory.from_xml(url, xml)
        if upnp_device:
            if upnp_device.manufacturer is not None and \
               upnp_device.manufacturer.lower() == 'yamaha corporation':
                upnp_device.workarounds.append(
                    pulseaudio_dlna.workarounds.YamahaWorkaround(xml))
            return DLNAMediaRenderer(upnp_device)
        return None

    @classmethod
    def from_header(cls, header):
        upnp_device = upnp.UpnpMediaRendererFactory.from_header(header)
        if upnp_device:
            return DLNAMediaRenderer(upnp_device)
        return None
