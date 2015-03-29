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

import re
import cgi
import requests
import urlparse
import socket
import logging
import random
import functools
import BeautifulSoup
import pulseaudio_dlna.pulseaudio
import pulseaudio_dlna.encoders
import pulseaudio_dlna.common


class UpnpService(object):

    SERVICE_TRANSPORT = 'transport'
    SERVICE_CONNECTION = 'connection'
    SERVICE_RENDERING = 'rendering'

    def __init__(self, ip, port, service):

        self.ip = ip
        self.port = port

        if service['service_type'].startswith('urn:schemas-upnp-org:service:AVTransport:'):
            self._type = self.SERVICE_TRANSPORT
        elif service['service_type'].startswith('urn:schemas-upnp-org:service:ConnectionManager:'):
            self._type = self.SERVICE_CONNECTION
        elif service['service_type'].startswith('urn:schemas-upnp-org:service:RenderingControl:'):
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


@functools.total_ordering
class UpnpMediaRenderer(object):

    REGISTER_XML = """<?xml version="1.0" encoding="{encoding}" standalone="yes"?>
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <u:SetAVTransportURI xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
            <InstanceID>0</InstanceID>
            <CurrentURI>{stream_url}</CurrentURI>
            <CurrentURIMetaData>{current_url_metadata}</CurrentURIMetaData>
        </u:SetAVTransportURI>
    </s:Body>
</s:Envelope>"""

    REGISTER_XML_METADATA = """<?xml version="1.0" encoding="{encoding}"?>
<DIDL-Lite xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dlna="urn:schemas-dlna-org:metadata-1-0/" xmlns:sec="http://www.sec.co.kr/" xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/">
    <item id="0" parentID="0" restricted="1">
        <upnp:class>object.item.audioItem.musicTrack</upnp:class>
        <dc:title>{title}</dc:title>
        <dc:creator>{creator}</dc:creator>
        <upnp:artist>{artist}</upnp:artist>
        <upnp:albumArtURI></upnp:albumArtURI>
        <upnp:album>{album}</upnp:album>
        <res protocolInfo="http-get:*:audio/mpeg:DLNA.ORG_OP=00;DLNA.ORG_FLAGS=01700000000000000000000000000000">{stream_url}</res>
    </item>
</DIDL-Lite>"""

    PLAY_XML = """<?xml version="1.0" encoding="{encoding}" standalone="yes"?>
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <u:Play xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
            <InstanceID>0</InstanceID>
            <Speed>1</Speed>
        </u:Play>
    </s:Body>
</s:Envelope>
"""

    STOP_XML = """<?xml version="1.0" encoding="{encoding}" standalone="yes"?>
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <u:Stop xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
            <InstanceID>0</InstanceID>
        </u:Stop>
    </s:Body>
</s:Envelope>"""

    PAUSE_XML = """<?xml version="1.0" encoding="{encoding}" standalone="yes"?>
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <u:Pause xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
            <InstanceID>0</InstanceID>
        </u:Pause>
    </s:Body>
</s:Envelope>"""

    GET_PROTOCOL_INFO_XML = """<?xml version="1.0" encoding="{encoding}" standalone="yes"?>
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <u:GetProtocolInfo xmlns:u="urn:schemas-upnp-org:service:ConnectionManager:1">
        </u:GetProtocolInfo>
    </s:Body>
</s:Envelope>"""

    PLAYING = 'playing'
    IDLE = 'idle'
    PAUSE = 'paused'

    ENCODING = 'utf-8'

    def __init__(self, name, ip, port, udn, services):
        name = name.strip()
        if name == '':
            name = 'Unnamed device (#{random_id})'.format(
                random_id=random.randint(1000, 9999))
        self.name = name
        self.short_name = self._short_name(name)
        self.ip = ip
        self.port = port
        self.udn = udn

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

        self.state = self.IDLE

        self.protocols = []

    def activate(self):
        self.get_protocol_info()

    def _short_name(self, name):
        return re.sub(r'[^a-z0-9]', '', name.lower())

    def _debug(self, action, url, headers, data, response):
        logging.debug(
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

    def get_encoder(self):
        for encoder in pulseaudio_dlna.common.supported_encoders:
            for mime_type in encoder.mime_types:
                if mime_type in self.protocols:
                    return encoder
        return None

    def register(self, stream_url):
        url = self.service_transport.control_url
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(encoding=self.ENCODING),
            'SOAPAction':
                '"{service_type}#SetAVTransportURI"'.format(
                    service_type=self.service_transport.service_type),
        }
        metadata = self.REGISTER_XML_METADATA.format(
            stream_url=stream_url,
            title='Live Audio',
            artist='PulseAudio on {}'.format(socket.gethostname()),
            creator='PulseAudio',
            album='Stream',
            encoding=self.ENCODING,
        )
        data = self.REGISTER_XML.format(
            stream_url=stream_url,
            current_url_metadata=cgi.escape(metadata),
            encoding=self.ENCODING,
        )
        response = requests.post(
            url, data=data.encode(self.ENCODING), headers=headers)
        self._debug('register', url, headers, data, response)
        return response.status_code

    def get_protocol_info(self):
        url = self.service_connection.control_url
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(encoding=self.ENCODING),
            'SOAPAction': '"{service_type}#GetProtocolInfo"'.format(
                service_type=self.service_connection.service_type),
        }
        data = self.GET_PROTOCOL_INFO_XML.format(
            encoding=self.ENCODING,
        )
        response = requests.post(
            url, data=data.encode(self.ENCODING), headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup.BeautifulSoup(response.content)
            try:
                self.protocols = []
                sinks = soup("sink")[0].text
                for sink in sinks.split(','):
                    http_get, w1, mime_type, w2 = sink.strip().split(':')
                    if mime_type.startswith('audio/'):
                        self.protocols.append(mime_type)
            except IndexError:
                logging.info(
                    'IndexError: No valid XML returned from {url}.'.format(url=url))

        self._debug('get_protocol_info', url, headers, data, response)
        return response.status_code

    def play(self):
        url = self.service_transport.control_url
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(encoding=self.ENCODING),
            'SOAPAction': '"{service_type}#Play"'.format(
                service_type=self.service_transport.service_type),
        }
        data = self.PLAY_XML.format(
            encoding=self.ENCODING,
        )
        response = requests.post(
            url, data=data.encode(self.ENCODING), headers=headers)
        if response.status_code == 200:
            self.state = self.PLAYING
        self._debug('play', url, headers, data, response)
        return response.status_code

    def stop(self):
        url = self.service_transport.control_url
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(encoding=self.ENCODING),
            'SOAPAction': '"{service_type}#Stop"'.format(
                service_type=self.service_transport.service_type),
        }
        data = self.STOP_XML.format(
            encoding=self.ENCODING,
        )
        response = requests.post(
            url, data=data.encode(self.ENCODING), headers=headers)
        if response.status_code == 200:
            self.state = self.IDLE
        self._debug('stop', url, headers, data, response)
        return response.status_code

    def pause(self):
        url = self.service_transport.control_url
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(encoding=self.ENCODING),
            'SOAPAction': '"{service_type}#Pause"'.format(
                service_type=self.service_transport.service_type),
        }
        data = self.PAUSE_XML.format(
            encoding=self.ENCODING,
        )
        response = requests.post(
            url, data=data.encode(self.ENCODING), headers=headers)
        if response.status_code == 200:
            self.state = self.PAUSE
        self._debug('pause', url, headers, data, response)
        return response.status_code

    def __eq__(self, other):
        if isinstance(other, UpnpMediaRenderer):
            return self.name == other.name
        if isinstance(other, pulseaudio_dlna.pulseaudio.PulseUpnpBridge):
            return self.name == other.upnp_device.name

    def __gt__(self, other):
        if isinstance(other, UpnpMediaRenderer):
            return self.name > other.name
        if isinstance(other, pulseaudio_dlna.pulseaudio.PulseUpnpBridge):
            return self.name > other.upnp_device.name

    def __str__(self):
        return '<UpnpMediaRenderer name="{}" short_name="{}" state="{}" protocols={}>'.format(
            self.name,
            self.short_name,
            self.state,
            ','.join(self.protocols),
        )


class CoinedUpnpMediaRenderer(UpnpMediaRenderer):
    def __init__(self, *args):
        UpnpMediaRenderer.__init__(self, *args)
        self.server_ip = None
        self.server_port = None

    def set_server_location(self, ip, port):
        self.server_ip = ip
        self.server_port = port

    def register(self):
        encoder = self.get_encoder()
        server_url = 'http://{ip}:{port}'.format(
            ip=self.server_ip,
            port=self.server_port,
        )
        stream_name = '/{stream_name}.{suffix}'.format(
            stream_name=self.short_name,
            suffix=encoder.suffix,
        )
        stream_url = urlparse.urljoin(server_url, stream_name)
        return UpnpMediaRenderer.register(self, stream_url)

    def __str__(self):
        return '<CoinedUpnpMediaRenderer name="{}" short_name="{}" state="{}" protocols={}>'.format(
            self.name,
            self.short_name,
            self.state,
            ','.join(self.protocols),
        )


class UpnpMediaRendererFactory(object):

    @classmethod
    def from_url(self, url, type_=UpnpMediaRenderer):
        try:
            response = requests.get(url)
            logging.debug('Response from upnp device ({url})\n'
                          '{response}'.format(url=url, response=response.text))
        except requests.exceptions.ConnectionError:
            logging.info(
                'Could no connect to {url}. '
                'Connection refused.'.format(url=url))
            return None
        soup = BeautifulSoup.BeautifulSoup(response.content)
        url_object = urlparse.urlparse(url)
        ip, port = url_object.netloc.split(':')
        services = []
        try:
            for service in soup.root.device.servicelist.findAll('service'):
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
            logging.info(
                'No valid XML returned from {url}.'.format(url=url))
            return None

    @classmethod
    def from_header(self, header, type_=UpnpMediaRenderer):
        header = re.findall(r"(?P<name>.*?): (?P<value>.*?)\r\n", header)
        header = {k.lower(): v for k, v in dict(header).items()}
        if header['location']:
            return self.from_url(header['location'], type_)
