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
import time
import traceback

import pulseaudio_dlna.pulseaudio
import pulseaudio_dlna.encoders
import pulseaudio_dlna.workarounds
import pulseaudio_dlna.codecs
import pulseaudio_dlna.rules
import pulseaudio_dlna.plugins.renderer
import upnp

logger = logging.getLogger('pulseaudio_dlna.plugins.dlna.renderer')


class MissingAttributeException(Exception):
    def __init__(self, command):
        Exception.__init__(
            self,
            'The command\'s "{}" response did not contain a required '
            'attribute!'.format(command.upper())
        )


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

    def activate(self, config):
        if config:
            self.set_rules_from_config(config)
        else:
            self.codecs = []
            mime_types = self.get_mime_types()
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

    def _register(
            self, stream_url, codec=None, artist=None, title=None, thumb=None):
        self._before_register()
        try:
            codec = codec or self.codec
            self.upnp_device.register(
                stream_url, codec.mime_type, artist, title, thumb)
        except Exception as e:
            raise e
        finally:
            self._after_register()

    def play(self, url=None, codec=None, artist=None, title=None, thumb=None):
        self._before_play()
        try:
            stream_url = url or self.get_stream_url()
            self._register(
                stream_url, codec, artist=artist, title=title, thumb=thumb)
            if pulseaudio_dlna.rules.DISABLE_PLAY_COMMAND in self.rules:
                logger.info(
                    'Disabled play command. Device should be playing ...')
            elif self._update_current_state():
                if self.state == self.STATE_STOPPED:
                    logger.info(
                        'Device state is stopped. Sending play command.')
                    self.upnp_device.play()
                elif self.state == self.STATE_PLAYING:
                    logger.info(
                        'Device state is playing. No need '
                        'to send play command.')
                else:
                    logger.info('Device state is unknown!')
                    return 500, 'Unknown device state!'
            else:
                logger.warning(
                    'Updating device state unsuccessful! '
                    'Sending play command.')
                self.upnp_device.play()
            self.state = self.STATE_PLAYING
            return 200, None
        except upnp.CommandFailedException as e:
            return 422, e
        except upnp.XmlParsingException as e:
            return 422, e
        except upnp.ConnectionErrorException as e:
            return 403, e
        except upnp.ConnectionTimeoutException as e:
            return 408, e
        except (pulseaudio_dlna.plugins.renderer.NoEncoderFoundException,
                pulseaudio_dlna.plugins.renderer.NoSuitableHostFoundException)\
                as e:
            return 500, e
        except Exception:
            traceback.print_exc()
            return 500, 'Unknown exception.'
        finally:
            self._after_play()

    def stop(self):
        self._before_stop()
        try:
            self.upnp_device.stop()
            self.state = self.STATE_STOPPED
            return 200, None
        except upnp.CommandFailedException as e:
            return 422, e
        except upnp.XmlParsingException as e:
            return 422, e
        except upnp.ConnectionErrorException as e:
            return 403, e
        except upnp.ConnectionTimeoutException as e:
            return 408, e
        except Exception:
            traceback.print_exc()
            return 500, 'Unknown exception.'
        finally:
            self._after_stop()

    def get_volume(self):
        try:
            d = self.upnp_device.get_volume()
            return int(d['GetVolumeResponse']['CurrentVolume'])
        except KeyError:
            logger.error(MissingAttributeException('get_volume'))
            return None
        except upnp.XmlParsingException as e:
            logger.error(e)
            return None
        except upnp.ConnectionErrorException as e:
            logger.error(e)
            return None
        except upnp.ConnectionTimeoutException as e:
            logger.error(e)
            return None

    def set_volume(self, volume):
        try:
            return self.upnp_device.set_volume(volume)
        except upnp.XmlParsingException as e:
            logger.error(e)
            return None
        except upnp.ConnectionErrorException as e:
            logger.error(e)
            return None
        except upnp.ConnectionTimeoutException as e:
            logger.error(e)
            return None

    def get_mute(self):
        try:
            d = self.upnp_device.get_mute()
            return int(d['GetMuteResponse']['CurrentMute']) != 0
        except KeyError:
            logger.error(MissingAttributeException('get_mute'))
            return None
        except upnp.XmlParsingException as e:
            logger.error(e)
            return None
        except upnp.ConnectionErrorException as e:
            logger.error(e)
            return None
        except upnp.ConnectionTimeoutException as e:
            logger.error(e)
            return None

    def set_mute(self, mute):
        try:
            return self.upnp_device.set_mute(mute)
        except upnp.XmlParsingException as e:
            logger.error(e)
            return None
        except upnp.ConnectionErrorException as e:
            logger.error(e)
            return None
        except upnp.ConnectionTimeoutException as e:
            logger.error(e)
            return None

    def get_mime_types(self):
        mime_types = []
        try:
            d = self.upnp_device.get_protocol_info()
            sinks = d['GetProtocolInfoResponse']['Sink']
            for sink in sinks.split(','):
                attributes = sink.strip().split(':')
                if len(attributes) >= 4:
                    mime_types.append(attributes[2])
            return mime_types
        except KeyError:
            logger.error(MissingAttributeException('get_protocol_info'))
            return None
        except upnp.XmlParsingException as e:
            logger.error(e)
            return None
        except upnp.ConnectionErrorException as e:
            logger.error(e)
            return None
        except upnp.ConnectionTimeoutException as e:
            logger.error(e)
            return None

    def get_transport_state(self):
        try:
            d = self.upnp_device.get_transport_info()
            state = d['GetTransportInfoResponse']['CurrentTransportState']
            return state
        except KeyError:
            logger.error(MissingAttributeException('get_transport_state'))
            return None
        except upnp.XmlParsingException as e:
            logger.error(e)
            return None
        except upnp.ConnectionErrorException as e:
            logger.error(e)
            return None
        except upnp.ConnectionTimeoutException as e:
            logger.error(e)
            return None

    def _update_current_state(self):
        start_time = time.time()
        while time.time() - start_time <= self.REQUEST_TIMEOUT:
            state = self.get_transport_state()
            if state is None:
                return False
            if state == upnp.UPNP_STATE_PLAYING:
                self.state = self.STATE_PLAYING
                return True
            elif state == upnp.UPNP_STATE_STOPPED:
                self.state = self.STATE_STOPPED
                return True
            time.sleep(1)
        return False


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
