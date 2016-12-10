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

import cgi
import requests
import urlparse
import logging
import pkg_resources
import lxml
import json
import xmltodict
import xml.parsers.expat

import byto

logger = logging.getLogger('upnp')


class ConnectionTimeoutException(Exception):
    def __init__(self, command):
        Exception.__init__(
            self,
            'The command "{}" timed out!'.format(
                command.upper())
        )


class ConnectionErrorException(Exception):
    def __init__(self, command):
        Exception.__init__(
            self,
            'The command "{}" could not connect to the host!'.format(
                command.upper())
        )


class XmlParsingException(Exception):
    def __init__(self, command):
        Exception.__init__(
            self,
            'The XML retrieved for command "{}" could not be parsed!'.format(
                command.upper())
        )


class CommandFailedException(Exception):
    def __init__(self, command, status_code):
        Exception.__init__(
            self,
            'The command "{}" failed with status code {}!'.format(
                command.upper(), status_code)
        )


class UpnpContentFlags(object):

    SENDER_PACED = 80000000
    LSOP_TIME_BASED_SEEK_SUPPORTED = 40000000
    LSOP_BYTE_BASED_SEEK_SUPPORTED = 20000000
    PLAY_CONTAINER_SUPPORTED = 10000000
    S0_INCREASING_SUPPORTED = 8000000
    SN_INCREASING_SUPPORTED = 4000000
    RTSP_PAUSE_SUPPORTED = 2000000
    STREAMING_TRANSFER_MODE_SUPPORTED = 1000000
    INTERACTIVE_TRANSFER_MODE_SUPPORTED = 800000
    BACKGROUND_TRANSFER_MODE_SUPPORTED = 400000
    CONNECTION_STALLING_SUPPORTED = 200000
    DLNA_VERSION_15_SUPPORTED = 100000

    def __init__(self, flags=None):
        self.flags = flags or []

    def __str__(self):
        return str(sum(self.flags)).zfill(8)


class UpnpContentFeatures(object):

    def __init__(self, support_time_seek=False, support_range=False,
                 transcoded=False, flags=None):
        self.support_time_seek = False
        self.support_range = False
        self.is_transcoded = False
        self.flags = UpnpContentFlags(flags or [])

    def __str__(self):
        return 'DLNA.ORG_OP={}{};DLNA.ORG_CI={};DLNA.ORG_FLAGS={}'.format(
            ('1' if self.support_time_seek else '0'),
            ('1' if self.support_range else '0'),
            ('1' if self.is_transcoded else '0'),
            (str(self.flags) + ('0' * 24)))


class UpnpService(object):

    SERVICE_TRANSPORT = 'transport'
    SERVICE_CONNECTION = 'connection'
    SERVICE_RENDERING = 'rendering'

    def __init__(self, ip, port, service):

        self.ip = ip
        self.port = port

        if service['service_type'].startswith(
                'urn:schemas-upnp-org:service:AVTransport:'):
            self._type = self.SERVICE_TRANSPORT
        elif service['service_type'].startswith(
                'urn:schemas-upnp-org:service:ConnectionManager:'):
            self._type = self.SERVICE_CONNECTION
        elif service['service_type'].startswith(
                'urn:schemas-upnp-org:service:RenderingControl:'):
            self._type = self.SERVICE_RENDERING
        else:
            self._type = None

        self._service_type = service['service_type']
        self._control_url = service['control_url']
        self._event_url = service['eventsub_url']

    @property
    def type(self):
        return self._type

    @property
    def service_type(self):
        return self._service_type

    @property
    def control_url(self):
        host = 'http://{ip}:{port}'.format(
            ip=self.ip,
            port=self.port,
        )
        return urlparse.urljoin(host, self._control_url)

    @property
    def event_url(self):
        host = 'http://{ip}:{port}'.format(
            ip=self.ip,
            port=self.port,
        )
        return urlparse.urljoin(host, self._event_url)


UPNP_STATE_PLAYING = 'PLAYING'
UPNP_STATE_STOPPED = 'STOPPED'
UPNP_STATE_PAUSED_PLAYBACK = 'PAUSED_PLAYBACK'
UPNP_STATE_PAUSED_RECORDING = 'PAUSED_RECORDING'
UPNP_STATE_RECORDING = 'RECORDING'
UPNP_STATE_TRANSITIONING = 'TRANSITIONING'
UPNP_STATE_NO_MEDIA_PRESENT = 'NO_MEDIA_PRESENT'


class UpnpMediaRendererController(object):

    ENCODING = 'utf-8'

    def __init__(self, access_url, ip, port, name, udn, model_name,
                 model_number, model_description, manufacturer, services,
                 timeout=10):
        self.state = None

        self.access_url = access_url
        self.ip = ip
        self.port = port
        self.name = name
        self.udn = udn
        self.model_name = model_name
        self.model_number = model_number
        self.model_description = model_description
        self.manufacturer = manufacturer

        self.xml = self._load_xml_files()
        self.service_transport = None
        self.service_connection = None
        self.service_rendering = None
        self.timeout = timeout

        self.content_features = UpnpContentFeatures(
            flags=[
                UpnpContentFlags.STREAMING_TRANSFER_MODE_SUPPORTED,
                UpnpContentFlags.BACKGROUND_TRANSFER_MODE_SUPPORTED,
                UpnpContentFlags.CONNECTION_STALLING_SUPPORTED,
                UpnpContentFlags.DLNA_VERSION_15_SUPPORTED
            ])

        for service in services:
            service = UpnpService(ip, port, service)
            if service.type == UpnpService.SERVICE_TRANSPORT:
                self.service_transport = service
            if service.type == UpnpService.SERVICE_CONNECTION:
                self.service_connection = service
            if service.type == UpnpService.SERVICE_RENDERING:
                self.service_rendering = service

        self._request = requests.Session()

    def _load_xml_files(self):
        content = {}
        self.xml_files = {
            'register': 'xml/register.xml',
            'register_metadata': 'xml/register_metadata.xml',
            'play': 'xml/play.xml',
            'stop': 'xml/stop.xml',
            'pause': 'xml/pause.xml',
            'get_protocol_info': 'xml/get_protocol_info.xml',
            'get_transport_info': 'xml/get_transport_info.xml',
            'get_volume': 'xml/get_volume.xml',
            'set_volume': 'xml/set_volume.xml',
            'get_mute': 'xml/get_mute.xml',
            'set_mute': 'xml/set_mute.xml',
        }
        for ident, path in self.xml_files.items():
            file_name = pkg_resources.resource_filename(
                'pulseaudio_dlna.plugins.dlna.upnp', path)
            with open(file_name, 'r') as f:
                content[ident] = unicode(f.read())
        return content

    def _debug_sent(self, url, headers, data):
        logger.debug('SENT {headers}:\n{url}\n{data}'.format(
            headers=headers,
            data=data,
            url=url,
        ))

    def _debug_received(self, status_code, headers, data):
        logger.debug('RECEIVED [{code}] - {headers}:\n{data}'.format(
            code=status_code,
            headers=headers,
            data=data,
        ))

    def register(
            self, stream_url, mime_type=None, artist=None, title=None,
            thumb=None, content_features=None):
        url = self.service_transport.control_url
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(
                    encoding=self.ENCODING),
            'SOAPAction':
                '"{service_type}#SetAVTransportURI"'.format(
                    service_type=self.service_transport.service_type),
        }
        content_features = content_features or self.content_features
        metadata = self.xml['register_metadata'].format(
            stream_url=stream_url,
            title=title or '',
            artist=artist or '',
            albumart=thumb or '',
            creator='',
            album='',
            encoding=self.ENCODING,
            mime_type=mime_type,
            content_features=str(content_features),
        )
        data = self.xml['register'].format(
            stream_url=stream_url,
            current_url_metadata=cgi.escape(metadata),
            encoding=self.ENCODING,
            service_type=self.service_transport.service_type,
        )
        try:
            response = None
            response = self._request.post(
                url, data=data.encode(self.ENCODING), headers=headers,
                timeout=self.timeout)
            return response
        except Exception as e:
            raise e
        finally:
            self._debug_sent(url, headers, data)
            if response:
                self._debug_received(
                    response.status_code, response.headers, response.content)

    def get_transport_info(self):
        url = self.service_transport.control_url
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(
                    encoding=self.ENCODING),
            'SOAPAction': '"{service_type}#GetTransportInfo"'.format(
                service_type=self.service_transport.service_type),
        }
        data = self.xml['get_transport_info'].format(
            encoding=self.ENCODING,
            service_type=self.service_transport.service_type,
        )
        try:
            response = None
            response = self._request.post(
                url, data=data.encode(self.ENCODING), headers=headers,
                timeout=self.timeout)
            return response
        except Exception as e:
            raise e
        finally:
            self._debug_sent(url, headers, data)
            if response:
                self._debug_received(
                    response.status_code, response.headers, response.content)

    def get_protocol_info(self):
        url = self.service_connection.control_url
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(
                    encoding=self.ENCODING),
            'SOAPAction': '"{service_type}#GetProtocolInfo"'.format(
                service_type=self.service_connection.service_type),
        }
        data = self.xml['get_protocol_info'].format(
            encoding=self.ENCODING,
            service_type=self.service_connection.service_type,
        )
        try:
            response = None
            response = self._request.post(
                url, data=data.encode(self.ENCODING), headers=headers,
                timeout=self.timeout)
            return response
        except Exception as e:
            raise e
        finally:
            self._debug_sent(url, headers, data)
            if response:
                self._debug_received(
                    response.status_code, response.headers, response.content)

    def get_volume(self, channel='Master'):
        url = self.service_rendering.control_url
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(
                    encoding=self.ENCODING),
            'SOAPAction': '"{service_type}#GetVolume"'.format(
                service_type=self.service_rendering.service_type),
        }
        data = self.xml['get_volume'].format(
            encoding=self.ENCODING,
            service_type=self.service_rendering.service_type,
            channel=channel,
        )
        try:
            response = None
            response = self._request.post(
                url, data=data.encode(self.ENCODING), headers=headers,
                timeout=self.timeout)
            return response
        except Exception as e:
            raise e
        finally:
            self._debug_sent(url, headers, data)
            if response:
                self._debug_received(
                    response.status_code, response.headers, response.content)

    def set_volume(self, volume, channel='Master'):
        url = self.service_rendering.control_url
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(
                    encoding=self.ENCODING),
            'SOAPAction': '"{service_type}#SetVolume"'.format(
                service_type=self.service_rendering.service_type),
        }
        data = self.xml['set_volume'].format(
            encoding=self.ENCODING,
            service_type=self.service_rendering.service_type,
            volume=volume,
            channel=channel,
        )
        try:
            response = None
            response = self._request.post(
                url, data=data.encode(self.ENCODING), headers=headers,
                timeout=self.timeout)
            return response
        except Exception as e:
            raise e
        finally:
            self._debug_sent(url, headers, data)
            if response:
                self._debug_received(
                    response.status_code, response.headers, response.content)

    def get_mute(self, channel='Master'):
        url = self.service_rendering.control_url
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(
                    encoding=self.ENCODING),
            'SOAPAction': '"{service_type}#GetMute"'.format(
                service_type=self.service_rendering.service_type),
        }
        data = self.xml['get_mute'].format(
            encoding=self.ENCODING,
            service_type=self.service_rendering.service_type,
            channel=channel,
        )
        try:
            response = None
            response = self._request.post(
                url, data=data.encode(self.ENCODING), headers=headers,
                timeout=self.timeout)
            return response
        except Exception as e:
            raise e
        finally:
            self._debug_sent(url, headers, data)
            if response:
                self._debug_received(
                    response.status_code, response.headers, response.content)

    def set_mute(self, muted, channel='Master'):
        url = self.service_rendering.control_url
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(
                    encoding=self.ENCODING),
            'SOAPAction': '"{service_type}#SetMute"'.format(
                service_type=self.service_rendering.service_type),
        }
        data = self.xml['set_mute'].format(
            encoding=self.ENCODING,
            service_type=self.service_rendering.service_type,
            muted='1' if muted else '0',
            channel=channel,
        )
        try:
            response = None
            response = self._request.post(
                url, data=data.encode(self.ENCODING), headers=headers,
                timeout=self.timeout)
            return response
        except Exception as e:
            raise e
        finally:
            self._debug_sent(url, headers, data)
            if response:
                self._debug_received(
                    response.status_code, response.headers, response.content)

    def play(self):
        url = self.service_transport.control_url
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(
                    encoding=self.ENCODING),
            'SOAPAction': '"{service_type}#Play"'.format(
                service_type=self.service_transport.service_type),
        }
        data = self.xml['play'].format(
            encoding=self.ENCODING,
            service_type=self.service_transport.service_type,
        )
        try:
            response = None
            response = self._request.post(
                url, data=data.encode(self.ENCODING), headers=headers,
                timeout=self.timeout)
            if response.status_code == 200:
                self.state = UPNP_STATE_PLAYING
            return response
        except Exception as e:
            raise e
        finally:
            self._debug_sent(url, headers, data)
            if response:
                self._debug_received(
                    response.status_code, response.headers, response.content)

    def stop(self):
        url = self.service_transport.control_url
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(
                    encoding=self.ENCODING),
            'SOAPAction': '"{service_type}#Stop"'.format(
                service_type=self.service_transport.service_type),
        }
        data = self.xml['stop'].format(
            encoding=self.ENCODING,
            service_type=self.service_transport.service_type,
        )
        try:
            response = None
            response = self._request.post(
                url, data=data.encode(self.ENCODING), headers=headers,
                timeout=self.timeout)
            if response.status_code == 200:
                self.state = UPNP_STATE_STOPPED
            return response
        except Exception as e:
            raise e
        finally:
            self._debug_sent(url, headers, data)
            if response:
                self._debug_received(
                    response.status_code, response.headers, response.content)

    def pause(self):
        url = self.service_transport.control_url
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(
                    encoding=self.ENCODING),
            'SOAPAction': '"{service_type}#Pause"'.format(
                service_type=self.service_transport.service_type),
        }
        data = self.xml['pause'].format(
            encoding=self.ENCODING,
            service_type=self.service_transport.service_type,
        )
        try:
            response = None
            response = self._request.post(
                url, data=data.encode(self.ENCODING), headers=headers,
                timeout=self.timeout)
            if response.status_code == 200:
                self.state = UPNP_STATE_PAUSED_PLAYBACK
            return response
        except Exception as e:
            raise e
        finally:
            self._debug_sent(url, headers, data)
            if response:
                self._debug_received(
                    response.status_code, response.headers, response.content)


class UpnpMediaRenderer(UpnpMediaRendererController):

    IGNORE_NAMESPACES = {
        'ns0': None,
        'ns1': None,
        's': None,
        'u': None,
    }

    def _convert_xml_to_dict(self, xml):
        d = xmltodict.parse(
            xml, process_namespaces=False,
            namespaces=self.IGNORE_NAMESPACES)
        return d

    def _convert_response_to_dict(self, response):
        if response.status_code == 200:
            try:
                d = self._convert_xml_to_dict(response.content)
                return d['Envelope']['Body']
            except TypeError:
                logger.error('No valid XML returned')
                return None

    def _debug_sent(self, url, headers, data):
        data = self._convert_xml_to_dict(data)
        logger.debug('SENT {headers}:\n{url}\n{data}'.format(
            headers=headers,
            data=json.dumps(data, indent=4, sort_keys=True),
            url=url,
        ))

    def _debug_received(self, status_code, headers, data):
        data = self._convert_xml_to_dict(data)
        logger.debug('RECEIVED [{code}] - {headers}:\n{data}'.format(
            code=status_code,
            headers=headers,
            data=json.dumps(data, indent=4, sort_keys=True),
        ))

    def register(self, *args, **kwargs):
        try:
            response = UpnpMediaRendererController.register(
                self, *args, **kwargs)
            if response.status_code == 200:
                return self._convert_response_to_dict(response)
            else:
                raise CommandFailedException(
                    'register', response.status_code)
        except xml.parsers.expat.ExpatError:
            raise XmlParsingException('register')
        except requests.exceptions.ConnectionError:
            raise ConnectionErrorException('register')
        except requests.exceptions.Timeout:
            raise ConnectionTimeoutException('register')

    def get_transport_info(self, *args, **kwargs):
        try:
            response = UpnpMediaRendererController.get_transport_info(
                self, *args, **kwargs)
            if response.status_code == 200:
                return self._convert_response_to_dict(response)
            else:
                raise CommandFailedException(
                    'get_transport_info', response.status_code)
        except xml.parsers.expat.ExpatError:
            raise XmlParsingException('get_transport_info')
        except requests.exceptions.ConnectionError:
            raise ConnectionErrorException('get_transport_info')
        except requests.exceptions.Timeout:
            raise ConnectionTimeoutException('get_transport_info')

    def get_protocol_info(self, *args, **kwargs):
        try:
            response = UpnpMediaRendererController.get_protocol_info(
                self, *args, **kwargs)
            if response.status_code == 200:
                return self._convert_response_to_dict(response)
            else:
                raise CommandFailedException(
                    'get_protocol_info', response.status_code)
        except xml.parsers.expat.ExpatError:
            raise XmlParsingException('get_protocol_info')
        except requests.exceptions.ConnectionError:
            raise ConnectionErrorException('get_protocol_info')
        except requests.exceptions.Timeout:
            raise ConnectionTimeoutException('get_protocol_info')

    def get_volume(self, *args, **kwargs):
        try:
            response = UpnpMediaRendererController.get_volume(
                self, *args, **kwargs)
            if response.status_code == 200:
                return self._convert_response_to_dict(response)
            else:
                raise CommandFailedException(
                    'get_volume', response.status_code)
        except xml.parsers.expat.ExpatError:
            raise XmlParsingException('get_volume')
        except requests.exceptions.ConnectionError:
            raise ConnectionErrorException('get_volume')
        except requests.exceptions.Timeout:
            raise ConnectionTimeoutException('get_volume')

    def set_volume(self, *args, **kwargs):
        try:
            response = UpnpMediaRendererController.set_volume(
                self, *args, **kwargs)
            if response.status_code == 200:
                return self._convert_response_to_dict(response)
            else:
                raise CommandFailedException(
                    'set_volume', response.status_code)
        except xml.parsers.expat.ExpatError:
            raise XmlParsingException('set_volume')
        except requests.exceptions.ConnectionError:
            raise ConnectionErrorException('set_volume')
        except requests.exceptions.Timeout:
            raise ConnectionTimeoutException('set_volume')

    def get_mute(self, *args, **kwargs):
        try:
            response = UpnpMediaRendererController.get_mute(
                self, *args, **kwargs)
            if response.status_code == 200:
                return self._convert_response_to_dict(response)
            else:
                raise CommandFailedException(
                    'get_mute', response.status_code)
        except xml.parsers.expat.ExpatError:
            raise XmlParsingException('get_mute')
        except requests.exceptions.ConnectionError:
            raise ConnectionErrorException('get_mute')
        except requests.exceptions.Timeout:
            raise ConnectionTimeoutException('get_mute')

    def set_mute(self, *args, **kwargs):
        try:
            response = UpnpMediaRendererController.set_mute(
                self, *args, **kwargs)
            if response.status_code == 200:
                return self._convert_response_to_dict(response)
            else:
                raise CommandFailedException(
                    'set_mute', response.status_code)
        except xml.parsers.expat.ExpatError:
            raise XmlParsingException('set_mute')
        except requests.exceptions.ConnectionError:
            raise ConnectionErrorException('set_mute')
        except requests.exceptions.Timeout:
            raise ConnectionTimeoutException('set_mute')

    def play(self, *args, **kwargs):
        try:
            response = UpnpMediaRendererController.play(
                self, *args, **kwargs)
            if response.status_code == 200:
                return self._convert_response_to_dict(response)
            else:
                raise CommandFailedException(
                    'play', response.status_code)
        except xml.parsers.expat.ExpatError:
            raise XmlParsingException('play')
        except requests.exceptions.ConnectionError:
            raise ConnectionErrorException('play')
        except requests.exceptions.Timeout:
            raise ConnectionTimeoutException('play')

    def stop(self, *args, **kwargs):
        try:
            response = UpnpMediaRendererController.stop(
                self, *args, **kwargs)
            if response.status_code == 200:
                return self._convert_response_to_dict(response)
            else:
                raise CommandFailedException(
                    'stop', response.status_code)
        except xml.parsers.expat.ExpatError:
            raise XmlParsingException('stop')
        except requests.exceptions.ConnectionError:
            raise ConnectionErrorException('stop')
        except requests.exceptions.Timeout:
            raise ConnectionTimeoutException('stop')

    def pause(self, *args, **kwargs):
        try:
            response = UpnpMediaRendererController.pause(
                self, *args, **kwargs)
            if response.status_code == 200:
                return self._convert_response_to_dict(response)
            else:
                raise CommandFailedException(
                    'pause', response.status_code)
        except xml.parsers.expat.ExpatError:
            raise XmlParsingException('pause')
        except requests.exceptions.ConnectionError:
            raise ConnectionErrorException('pause')
        except requests.exceptions.Timeout:
            raise ConnectionTimeoutException('pause')


class UpnpMediaRendererFactory(object):

    NOTIFICATION_TYPES = [
        'urn:schemas-upnp-org:device:MediaRenderer:1',
        'urn:schemas-upnp-org:device:MediaRenderer:2',
    ]

    @classmethod
    def from_url(cls, url):
        try:
            response = requests.get(url, timeout=5)
            logger.debug('Response from UPNP device ({url})\n'
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

        def process_xml(url, xml_root, xml):
            url_object = urlparse.urlparse(url)
            ip, port = url_object.netloc.split(':')
            services = []
            for device in xml_root.findall('.//{*}device'):
                device_type = device.find('{*}deviceType')
                device_friendlyname = device.find('{*}friendlyName')
                device_udn = device.find('{*}UDN')
                device_modelname = device.find('{*}modelName')
                device_modelnumber = device.find('{*}modelNumber')
                device_modeldescription = device.find('{*}modelDescription')
                device_manufacturer = device.find('{*}manufacturer')

                if device_type.text not in cls.NOTIFICATION_TYPES:
                    continue

                for service in device.findall('.//{*}service'):
                    service = {
                        'service_type': service.find('{*}serviceType').text,
                        'service_id': service.find('{*}serviceId').text,
                        'scpd_url': service.find('{*}SCPDURL').text,
                        'control_url': service.find('{*}controlURL').text,
                        'eventsub_url': service.find('{*}eventSubURL').text,
                    }
                    services.append(service)

                upnp_device = UpnpMediaRenderer(
                    access_url=url,
                    ip=unicode(ip),
                    port=port,
                    name=unicode(device_friendlyname.text),
                    udn=unicode(device_udn.text),
                    model_name=unicode(device_modelname.text) if (
                        device_modelname is not None) else None,
                    model_number=unicode(device_modelnumber.text) if (
                        device_modelnumber is not None) else None,
                    model_description=unicode(device_modeldescription.text) if (
                        device_modeldescription is not None) else None,
                    manufacturer=unicode(device_manufacturer.text) if (
                        device_manufacturer is not None) else None,
                    services=services,
                )
                return upnp_device
        try:
            xml_root = lxml.etree.fromstring(xml)
            return process_xml(url, xml_root, xml)
        except:
            logger.debug('Got broken xml, trying to fix it.')
            xml = byto.repair_xml(xml)
            try:
                xml_root = lxml.etree.fromstring(xml)
                return process_xml(url, xml_root, xml)
            except:
                import traceback
                traceback.print_exc()
                logger.error('No valid XML returned from {url}.'.format(
                    url=url))
                return None

    @classmethod
    def from_header(cls, header):
        if header.get('location', None):
            return cls.from_url(header['location'])
