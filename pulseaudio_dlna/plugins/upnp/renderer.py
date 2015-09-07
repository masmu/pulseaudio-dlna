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
import socket
import logging
import pkg_resources
import BeautifulSoup
import pulseaudio_dlna.pulseaudio
import pulseaudio_dlna.encoders
import pulseaudio_dlna.common
import pulseaudio_dlna.plugins.renderer

logger = logging.getLogger('pulseaudio_dlna.plugins.upnp.renderer')


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


class UpnpMediaRenderer(pulseaudio_dlna.plugins.renderer.BaseRenderer):

    ENCODING = 'utf-8'

    def __init__(self, name, ip, port, udn, services, encoder=None):
        pulseaudio_dlna.plugins.renderer.BaseRenderer.__init__(self, udn)
        self.flavour = 'DLNA'
        self.name = name
        self.ip = ip
        self.port = port
        self.state = self.IDLE
        self.encoder = encoder
        self.codecs = []

        self.xml = self._load_xml_files()
        self.service_transport = None
        self.service_connection = None
        self.service_rendering = None

        for service in services:
            service = UpnpService(ip, port, service)
            if service.type == UpnpService.SERVICE_TRANSPORT:
                self.service_transport = service
            if service.type == UpnpService.SERVICE_CONNECTION:
                self.service_connection = service
            if service.type == UpnpService.SERVICE_RENDERING:
                self.service_rendering = service

    def activate(self, config):
        if config:
            self.set_codecs_from_config(config)
        else:
            self.get_protocol_info()

    def _load_xml_files(self):
        content = {}
        self.xml_files = {
            'register': 'xml/register.xml',
            'register_metadata': 'xml/register_metadata.xml',
            'play': 'xml/play.xml',
            'stop': 'xml/stop.xml',
            'pause': 'xml/pause.xml',
            'get_protocol_info': 'xml/get_protocol_info.xml',
        }
        for ident, path in self.xml_files.items():
            file_name = pkg_resources.resource_filename(
                'pulseaudio_dlna.plugins.upnp', path)
            with open(file_name, 'r') as f:
                content[ident] = unicode(f.read())
        return content

    def _debug(self, action, url, headers, data, response):
        logger.debug(
            'sending {action} to {url}:\n'
            ' - headers:\n{headers}\n'
            ' - data:\n{data}'
            ' - result: {status_code}\n{result}'.format(
                action=action.upper(),
                url=url,
                headers=headers,
                data=data,
                status_code=response.status_code,
                result=response.text))

    def register(self, stream_url):
        url = self.service_transport.control_url
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(
                    encoding=self.ENCODING),
            'SOAPAction':
                '"{service_type}#SetAVTransportURI"'.format(
                    service_type=self.service_transport.service_type),
        }
        content_features = UpnpContentFeatures(
            flags=[
                UpnpContentFlags.STREAMING_TRANSFER_MODE_SUPPORTED,
                UpnpContentFlags.BACKGROUND_TRANSFER_MODE_SUPPORTED,
                UpnpContentFlags.CONNECTION_STALLING_SUPPORTED,
                UpnpContentFlags.DLNA_VERSION_15_SUPPORTED
            ])
        mime_type = self.codec.mime_type
        if isinstance(self.codec, pulseaudio_dlna.codecs.WavCodec):
            mime_type = 'audio/mpeg'
        metadata = self.xml['register_metadata'].format(
            stream_url=stream_url,
            title='Live Audio',
            artist='PulseAudio on {}'.format(socket.gethostname()),
            creator='PulseAudio',
            album='Stream',
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
            response = requests.post(
                url, data=data.encode(self.ENCODING),
                headers=headers, timeout=3)
            self._debug('register', url, headers, data, response)
            return response.status_code
        except requests.exceptions.Timeout:
            logger.error(
                'Could no connect to {url}. '
                'Connection timeout.'.format(url=url))
            return 408

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
        response = requests.post(
            url, data=data.encode(self.ENCODING), headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup.BeautifulSoup(response.content)
            try:
                self.codecs = []
                sinks = soup('sink')[0].text
                logger.debug('Got the following mime types: "{}"'.format(sinks))
                for sink in sinks.split(','):
                    attributes = sink.strip().split(':')
                    if len(attributes) >= 4:
                        mime_type = attributes[2]
                        for codec in pulseaudio_dlna.common.supported_codecs:
                            if codec.accepts(mime_type.lower()) and \
                               codec not in self.codecs:
                                self.codecs.append(type(codec)(mime_type))
                self.prioritize_codecs()
            except IndexError:
                logger.error(
                    'IndexError: No valid XML returned from {url}.'.format(
                        url=url))

        self._debug('get_protocol_info', url, headers, data, response)
        return response.status_code

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
            response = requests.post(
                url, data=data.encode(self.ENCODING),
                headers=headers, timeout=3)
            if response.status_code == 200:
                self.state = self.PLAYING
            self._debug('play', url, headers, data, response)
            return response.status_code
        except requests.exceptions.Timeout:
            logger.error(
                'Could no connect to {url}. '
                'Connection timeout.'.format(url=url))
            return 408

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
            response = requests.post(
                url, data=data.encode(self.ENCODING),
                headers=headers, timeout=3)
            if response.status_code == 200:
                self.state = self.IDLE
            self._debug('stop', url, headers, data, response)
            return response.status_code
        except requests.exceptions.Timeout:
            logger.error(
                'Could no connect to {url}. '
                'Connection timeout.'.format(url=url))
            return 408

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
            response = requests.post(
                url, data=data.encode(self.ENCODING),
                headers=headers, timeout=3)
            if response.status_code == 200:
                self.state = self.PAUSE
            self._debug('pause', url, headers, data, response)
            return response.status_code
        except requests.exceptions.Timeout:
            logger.error(
                'Could no connect to {url}. '
                'Connection timeout.'.format(url=url))
            return 408


class CoinedUpnpMediaRenderer(
        pulseaudio_dlna.plugins.renderer.CoinedBaseRendererMixin, UpnpMediaRenderer):

    def play(self):
        try:
            stream_url = self.get_stream_url()
            if UpnpMediaRenderer.register(self, stream_url) == 200:
                return UpnpMediaRenderer.play(self)
            else:
                logger.error('"{}" registering failed!'.format(self.name))
        except requests.exceptions.ConnectionError:
            logger.error('The device refused the connection!')
            return 404
        except pulseaudio_dlna.plugins.renderer.NoSuitableEncoderFoundException:
            logger.error('Could not find a suitable encoder!')
            return 500


class UpnpMediaRendererFactory(object):

    ST_HEADER = 'urn:schemas-upnp-org:device:MediaRenderer:1'

    @classmethod
    def from_url(self, url, type_=UpnpMediaRenderer):
        try:
            response = requests.get(url, timeout=5)
            logger.debug('Response from UPNP device ({url})\n'
                         '{response}'.format(url=url, response=response.text))
        except requests.exceptions.Timeout:
            logger.info(
                'Could no connect to {url}. '
                'Connection timeout.'.format(url=url))
            return None
        except requests.exceptions.ConnectionError:
            logger.info(
                'Could no connect to {url}. '
                'Connection refused.'.format(url=url))
            return None
        soup = BeautifulSoup.BeautifulSoup(response.content)
        url_object = urlparse.urlparse(url)
        ip, port = url_object.netloc.split(':')
        services = []
        try:
            for device in soup.root.findAll('device'):
                if device.devicetype.text != self.ST_HEADER:
                    continue
                for service in device.findAll('service'):
                    service = {
                        'service_type': service.servicetype.text,
                        'service_id': service.serviceid.text,
                        'scpd_url': service.scpdurl.text,
                        'control_url': service.controlurl.text,
                        'eventsub_url': service.eventsuburl.text,
                    }
                    services.append(service)
                upnp_device = type_(
                    soup.root.device.friendlyname.text,
                    ip,
                    port,
                    soup.root.device.udn.text,
                    services)
                return upnp_device
        except AttributeError:
            logger.error(
                'No valid XML returned from {url}.'.format(url=url))
            return None

    @classmethod
    def from_header(self, header, type_=UpnpMediaRenderer):
        if header.get('location', None):
            return self.from_url(header['location'], type_)
