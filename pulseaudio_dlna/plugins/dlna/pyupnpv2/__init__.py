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
import urllib.parse
import logging
import collections
import urllib.parse
import os
import lxml
import lxml.builder

from . import byto

logger = logging.getLogger('pyupnpv2')


class ConnectionTimeoutException(Exception):
    def __init__(self, command):
        Exception.__init__(
            self,
            'The command "{}" timed out!'.format(command)
        )
        self.command = command


class ConnectionErrorException(Exception):
    def __init__(self, command):
        Exception.__init__(
            self,
            'The command "{}" could not connect to the host!'.format(command)
        )
        self.command = command


class XmlParsingException(Exception):
    def __init__(self, xml):
        Exception.__init__(
            self,
            'The following XML could not get parsed!\n"{}"'.format(xml)
        )
        self.xml = xml


class CommandFailedException(Exception):
    def __init__(self, command, status_code):
        Exception.__init__(
            self,
            'The command "{}" failed with status code {}!'.format(
                command, status_code)
        )
        self.command = command
        self.status_code = status_code


class UnsupportedActionException(Exception):
    def __init__(self, action_name):
        Exception.__init__(
            self,
            'The action "{}" is not supported!'.format(action_name)
        )
        self.action_name = action_name


class UnsupportedServiceTypeException(Exception):
    def __init__(self, service_type):
        Exception.__init__(
            self,
            'Service type "{}" is not supported!'.format(service_type)
        )
        self.service_type = service_type


class MissingServiceException(Exception):
    def __init__(self, service_type):
        Exception.__init__(
            self,
            'The service type "{}" is missing!'.format(service_type)
        )
        self.service_type = service_type


UPNP_STATE_PLAYING = 'PLAYING'
UPNP_STATE_STOPPED = 'STOPPED'
UPNP_STATE_PAUSED_PLAYBACK = 'PAUSED_PLAYBACK'
UPNP_STATE_PAUSED_RECORDING = 'PAUSED_RECORDING'
UPNP_STATE_RECORDING = 'RECORDING'
UPNP_STATE_TRANSITIONING = 'TRANSITIONING'
UPNP_STATE_NO_MEDIA_PRESENT = 'NO_MEDIA_PRESENT'

SOAP_ENV_NS = 'http://schemas.xmlsoap.org/soap/envelope/'
SOAP_ENC_NS = 'http://schemas.xmlsoap.org/soap/encoding/'
DC_NS = 'http://purl.org/dc/elements/1.1/'
SEC_NS = 'http://www.sec.co.kr/'
DLNA_NS = 'urn:schemas-dlna-org:metadata-1-0/'
UPNP_NS = 'urn:schemas-upnp-org:metadata-1-0/upnp/'
DIDL_NS = 'urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/'

SERVICE_TYPE_AVTRANSPORT = \
    'urn:schemas-upnp-org:service:AVTransport'
SERVICE_TYPE_CONNECTION_MANAGER = \
    'urn:schemas-upnp-org:service:ConnectionManager'
SERVICE_TYPE_RENDERING_CONTROL = \
    'urn:schemas-upnp-org:service:RenderingControl'


def _convert_xml_to_dict(xml, strip_namespaces=True):

    from collections import defaultdict

    if strip_namespaces:
        def _tag_name(element):
            return lxml.etree.QName(element).localname
    else:
        def _tag_name(element):
            return element.tag

    # taken from http://stackoverflow.com/questions/2148119 and adjusted
    def etree_to_dict(t):
        d = {
            _tag_name(t): {} if t.attrib else None
        }
        children = list(t)
        if children:
            dd = defaultdict(list)
            for dc in map(etree_to_dict, children):
                for k, v in list(dc.items()):
                    dd[k].append(v)
            d = {
                _tag_name(t): {
                    k: v[0] if len(v) == 1 else v for k, v in list(dd.items())
                }
            }
        if t.attrib:
            d[_tag_name(t)].update(
                ('@' + k, v) for k, v in list(t.attrib.items())
            )
        if t.text:
            text = t.text.strip()
            if children or t.attrib:
                if text:
                    d[_tag_name(t)]['#text'] = text
            else:
                d[_tag_name(t)] = text
        return d

    try:
        xml = lxml.etree.fromstring(xml)
        return etree_to_dict(xml)
    except Exception:
        raise XmlParsingException(xml)


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


class UpnpServiceFactory(object):

    @classmethod
    def from_dict(cls, ip, port, service, access_url, request):
        if service['service_type'].startswith(
                '{}:'.format(SERVICE_TYPE_AVTRANSPORT)):
            return UpnpAVTransportService(
                ip, port, service, access_url, request)
        elif service['service_type'].startswith(
                '{}:'.format(SERVICE_TYPE_CONNECTION_MANAGER)):
            return UpnpConnectionManagerService(
                ip, port, service, access_url, request)
        elif service['service_type'].startswith(
                '{}:'.format(SERVICE_TYPE_RENDERING_CONTROL)):
            return UpnpRenderingControlService(
                ip, port, service, access_url, request)
        else:
            raise UnsupportedServiceTypeException(service['service_type'])


class UpnpService(object):

    ENCODING = 'utf-8'
    TIMEOUT = 10

    def __init__(self, ip, port, service, access_url, request=None):

        self.ip = ip
        self.port = port
        self.supported_actions = []
        self.access_url = access_url

        self._request = request or requests
        self._service_type = service['service_type']
        self._control_url = self._ensure_absolute_url(service['control_url'])
        self._event_url = self._ensure_absolute_url(service['eventsub_url'])
        self._scpd_url = self._ensure_absolute_url(service['scpd_url'])

        self._update_supported_actions()

    def _ensure_absolute_url(self, url):
        if not url.startswith('/'):
            url_object = urllib.parse.urlparse(self.access_url)
            access_url_path = os.path.dirname(url_object.path)
            return os.path.join('/', access_url_path, url)
        else:
            return url

    def _update_supported_actions(self):
        self.supported_actions = []
        response = self._request.get(self.scpd_url)
        if response.status_code == 200:
            try:
                xml = response.content
                d = _convert_xml_to_dict(xml)
                actions = d['scpd']['actionList']['action']
                if type(actions) == list:
                    for action in d['scpd']['actionList']['action']:
                        self.supported_actions.append(action['name'])
                else:
                    self.supported_actions.append(actions['name'])
            except (ValueError, KeyError):
                raise XmlParsingException(xml)

    def _generate_soap_xml(
            self, command, service_type, dict_,
            xml_declaration=True, pretty_print=False, encoding='utf-8'):

        def _add_dict(root, dict_):
            for tag, value in list(dict_.items()):
                if isinstance(value, dict):
                    element = lxml.etree.Element(tag)
                    _add_dict(element, value)
                    root.append(element)
                else:
                    element = lxml.etree.Element(tag)
                    element.text = value
                    root.append(element)

        command_maker = lxml.builder.ElementMaker(
            namespace=service_type, nsmap={'u': service_type})

        cmd_xml = command_maker(command)
        _add_dict(cmd_xml, dict_)

        soap_maker = lxml.builder.ElementMaker(
            namespace=SOAP_ENV_NS, nsmap={'s': SOAP_ENV_NS})
        envelope_xml = soap_maker.Envelope(
            soap_maker.Body(cmd_xml)
        )
        tag_name = '{{{prefix}}}encodingStyle'.format(prefix=SOAP_ENV_NS)
        envelope_xml.attrib[tag_name] = SOAP_ENC_NS

        return lxml.etree.tostring(
            envelope_xml, xml_declaration=xml_declaration, encoding=encoding,
            pretty_print=pretty_print)

    def _generate_didl_xml(
            self, title, creator, artist, album_art, album, protocol_info,
            stream_url,
            pretty_print=False, xml_declaration=True, encoding='utf-8'):

        didl_maker = lxml.builder.ElementMaker(namespace=DIDL_NS, nsmap={
            None: DIDL_NS,
            'dc': DC_NS,
            'dlna': DLNA_NS,
            'sec': SEC_NS,
            'upnp': UPNP_NS,
        })
        upnp_maker = lxml.builder.ElementMaker(namespace=UPNP_NS)
        dc_maker = lxml.builder.ElementMaker(namespace=DC_NS)

        didl_xml = didl_maker(
            'DIDL-Lite',
            didl_maker.item(
                {'id': '0', 'parentID': '0', 'restricted': '1'},
                upnp_maker('class', 'object.item.audioItem.musicTrack'),
                dc_maker('title', title),
                dc_maker('creator', creator),
                upnp_maker('artist', artist),
                upnp_maker('albumArtURI', album_art),
                upnp_maker('album', album),
                didl_maker('res', {'protocolInfo': protocol_info}, stream_url),
            )
        )
        return lxml.etree.tostring(
            didl_xml, xml_declaration=xml_declaration, encoding=encoding,
            pretty_print=pretty_print)

    def _get_headers(self, action_name):
        return {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(
                    encoding=self.ENCODING),
            'SOAPAction':
                '"{service_type}#{action_name}"'.format(
                    service_type=self.service_type,
                    action_name=action_name),
        }

    def _do_post_request(self, url, headers, data):
        try:
            response = None
            response = self._request.post(
                url, data=data, headers=headers,
                timeout=self.TIMEOUT)
            return response
        finally:
            self._debug_sent(url, headers, data)
            if response is not None:
                self._debug_received(
                    response.status_code, response.headers, response.content)

    def _execute_action(self, action_name, dict_):
        if action_name not in self.supported_actions:
            raise UnsupportedActionException(action_name)
        headers = self._get_headers(action_name)
        data = self._generate_soap_xml(
            action_name, self.service_type, dict_, encoding=self.ENCODING)
        try:
            response = self._do_post_request(self.control_url, headers, data)
        except requests.exceptions.ConnectionError:
            raise ConnectionErrorException(action_name)
        except requests.exceptions.Timeout:
            raise ConnectionTimeoutException(action_name)
        if response.status_code == 200:
            return response
        else:
            raise CommandFailedException(action_name, response.status_code)

    def _debug_sent(self, url, headers, data):
        logger.debug('SENT {headers}:\nURL: {url}\n{data}'.format(
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

    @property
    def service_type(self):
        return self._service_type

    @property
    def control_url(self):
        host = 'http://{ip}:{port}'.format(
            ip=self.ip,
            port=self.port,
        )
        return urllib.parse.urljoin(host, self._control_url)

    @property
    def event_url(self):
        host = 'http://{ip}:{port}'.format(
            ip=self.ip,
            port=self.port,
        )
        return urllib.parse.urljoin(host, self._event_url)

    @property
    def scpd_url(self):
        host = 'http://{ip}:{port}'.format(
            ip=self.ip,
            port=self.port,
        )
        return urllib.parse.urljoin(host, self._scpd_url)


class UpnpAVTransportService(UpnpService):

    def __init__(self, *args, **kwargs):
        UpnpService.__init__(self, *args, **kwargs)
        self.content_features = UpnpContentFeatures(
            flags=[
                UpnpContentFlags.STREAMING_TRANSFER_MODE_SUPPORTED,
                UpnpContentFlags.BACKGROUND_TRANSFER_MODE_SUPPORTED,
                UpnpContentFlags.CONNECTION_STALLING_SUPPORTED,
                UpnpContentFlags.DLNA_VERSION_15_SUPPORTED
            ])

    def set_av_transport_uri(
            self, stream_url, mime_type=None, artist=None, title=None,
            thumb=None, content_features=None, instance_id='0'):
        metadata = self._generate_didl_xml(
            title=title or '',
            creator='',
            artist=artist or '',
            album_art=thumb or '',
            album='',
            protocol_info='http-get:*:{}:{}'.format(
                mime_type, str(content_features or self.content_features)),
            stream_url=stream_url,
        )
        return self._execute_action(
            'SetAVTransportURI', collections.OrderedDict([
                ('InstanceID', instance_id),
                ('CurrentURI', stream_url),
                ('CurrentURIMetaData', metadata),
            ]))

    def get_transport_info(self, instance_id='0'):
        return self._execute_action(
            'GetTransportInfo', collections.OrderedDict([
                ('InstanceID', instance_id),
            ]))

    def play(self, speed='1', instance_id='0'):
        return self._execute_action(
            'Play', collections.OrderedDict([
                ('InstanceID', instance_id),
                ('Speed', speed),
            ]))

    def stop(self, instance_id='0'):
        return self._execute_action(
            'Stop', collections.OrderedDict([
                ('InstanceID', instance_id),
            ]))

    def pause(self, instance_id='0'):
        return self._execute_action(
            'Pause', collections.OrderedDict([
                ('InstanceID', instance_id),
            ]))


class UpnpConnectionManagerService(UpnpService):

    def get_position_info(self, instance_id='0'):
        return self._execute_action(
            'GetPositionInfo', collections.OrderedDict([
                ('InstanceID', instance_id),
            ]))

    def get_protocol_info(self):
        return self._execute_action('GetProtocolInfo', {})


class UpnpRenderingControlService(UpnpService):

    def get_volume(self, channel='Master', instance_id='0'):
        return self._execute_action(
            'GetVolume', collections.OrderedDict([
                ('Channel', channel),
                ('InstanceID', instance_id),
            ]))

    def set_volume(self, volume, channel='Master', instance_id='0'):
        return self._execute_action(
            'SetVolume', collections.OrderedDict([
                ('DesiredVolume', volume),
                ('Channel', channel),
                ('InstanceID', instance_id),
            ]))

    def get_mute(self, channel='Master', instance_id='0'):
        return self._execute_action(
            'GetMute', collections.OrderedDict([
                ('Channel', channel),
                ('InstanceID', instance_id),
            ]))

    def set_mute(self, muted, channel='Master', instance_id='0'):
        return self._execute_action(
            'SetMute', collections.OrderedDict([
                ('DesiredMute', '1' if muted else '0'),
                ('Channel', channel),
                ('InstanceID', instance_id),
            ]))


class UpnpMediaRenderer(object):

    def __init__(self, description_xml, access_url, ip, port, name, udn,
                 model_name, model_number, model_description,
                 manufacturer, services, timeout=10):
        self.state = None

        self.description_xml = description_xml
        self.access_url = access_url

        self.ip = ip
        self.port = port
        self.name = name
        self.udn = udn
        self.model_name = model_name
        self.model_number = model_number
        self.model_description = model_description
        self.manufacturer = manufacturer

        self.timeout = timeout
        self._request = requests.Session()

        self.av_transport = None
        self.connection_manager = None
        self.rendering_control = None

        for service in services:
            try:
                service = UpnpServiceFactory.from_dict(
                    ip, port, service, access_url, self._request)
                if isinstance(service, UpnpAVTransportService):
                    self.av_transport = service
                if isinstance(service, UpnpConnectionManagerService):
                    self.connection_manager = service
                if isinstance(service, UpnpRenderingControlService):
                    self.rendering_control = service
            except UnsupportedServiceTypeException:
                pass

        if not self.av_transport:
            raise MissingServiceException(SERVICE_TYPE_AVTRANSPORT)
        if not self.connection_manager:
            raise MissingServiceException(SERVICE_TYPE_CONNECTION_MANAGER)
        if not self.rendering_control:
            raise MissingServiceException(SERVICE_TYPE_RENDERING_CONTROL)

    def _convert_response_to_dict(self, response):
        try:
            xml = response.content
            d = _convert_xml_to_dict(xml)
            return d['Envelope']['Body']
        except ValueError:
            raise XmlParsingException(xml)

    def set_av_transport_uri(self, *args, **kwargs):
        response = self.av_transport.set_av_transport_uri(*args, **kwargs)
        return self._convert_response_to_dict(response)

    def play(self, *args, **kwargs):
        response = self.av_transport.play(*args, **kwargs)
        if response.status_code == 200:
            self.state = UPNP_STATE_PLAYING
        return self._convert_response_to_dict(response)

    def stop(self, *args, **kwargs):
        response = self.av_transport.stop(*args, **kwargs)
        if response.status_code == 200:
            self.state = UPNP_STATE_STOPPED
        return self._convert_response_to_dict(response)

    def pause(self, *args, **kwargs):
        response = self.av_transport.pause(*args, **kwargs)
        if response.status_code == 200:
            self.state = UPNP_STATE_PAUSED_PLAYBACK
        return self._convert_response_to_dict(response)

    def get_transport_info(self, *args, **kwargs):
        response = self.av_transport.get_transport_info(*args, **kwargs)
        return self._convert_response_to_dict(response)

    def get_position_info(self, *args, **kwargs):
        response = self.connection_manager.get_position_info(*args, **kwargs)
        return self._convert_response_to_dict(response)

    def get_protocol_info(self, *args, **kwargs):
        response = self.connection_manager.get_protocol_info(*args, **kwargs)
        return self._convert_response_to_dict(response)

    def get_volume(self, *args, **kwargs):
        response = self.rendering_control.get_volume(*args, **kwargs)
        return self._convert_response_to_dict(response)

    def set_volume(self, *args, **kwargs):
        response = self.rendering_control.set_volume(*args, **kwargs)
        return self._convert_response_to_dict(response)

    def get_mute(self, *args, **kwargs):
        response = self.rendering_control.get_mute(*args, **kwargs)
        return self._convert_response_to_dict(response)

    def set_mute(self, *args, **kwargs):
        response = self.rendering_control.set_mute(*args, **kwargs)
        return self._convert_response_to_dict(response)


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
            url_object = urllib.parse.urlparse(url)
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

                try:
                    upnp_device = UpnpMediaRenderer(
                        description_xml=xml,
                        access_url=url,
                        ip=str(ip),
                        port=port,
                        name=str(device_friendlyname.text),
                        udn=str(device_udn.text),
                        model_name=str(
                            device_modelname.text) if (
                                device_modelname is not None) else None,
                        model_number=str(
                            device_modelnumber.text) if (
                                device_modelnumber is not None) else None,
                        model_description=str(
                            device_modeldescription.text) if (
                                device_modeldescription is not None) else None,
                        manufacturer=str(
                            device_manufacturer.text) if (
                                device_manufacturer is not None) else None,
                        services=services,
                    )
                    return upnp_device
                except MissingServiceException as e:
                    logger.warning(
                        'The device "{}" did not specify a "{}" service. '
                        'Device skipped!'.format(
                            device_friendlyname.text, e.service_type))
                except XmlParsingException as e:
                    logger.warning(
                        'The device "{}" did not specify a valid action list. '
                        'Device skipped! \n{}'.format(
                            device_friendlyname.text, e.xml))
        try:
            xml = xml.decode("utf-8").replace(" urn:microsoft-com:wmc-1-0", "urn:microsoft-com:wmc-1-0").encode("utf-8")
            xml_root = lxml.etree.fromstring(xml)
            return process_xml(url, xml_root, xml)
        except Exception:
            logger.debug('Got broken xml, trying to fix it.')
            xml = byto.repair_xml(xml)
            try:
                xml_root = lxml.etree.fromstring(xml)
                return process_xml(url, xml_root, xml)
            except Exception:
                import traceback
                traceback.print_exc()
                logger.error('No valid XML returned from {url}.'.format(
                    url=url))
                return None

    @classmethod
    def from_header(cls, header):
        if header.get('location', None):
            return cls.from_url(header['location'])
