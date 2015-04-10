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
        pulseaudio_dlna.plugins.renderer.BaseRenderer.__init__(self)
        self.flavour = 'DLNA'
        self.name = name
        self.ip = ip
        self.port = port
        self.state = self.IDLE
        self.encoder = encoder
        self.protocols = []

        self.udn = udn
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

    def activate(self):
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
        metadata = self.xml['register_metadata'].format(
            stream_url=stream_url,
            title='Live Audio',
            artist='PulseAudio on {}'.format(socket.gethostname()),
            creator='PulseAudio',
            album='Stream',
            encoding=self.ENCODING,
        )
        data = self.xml['register'].format(
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
                'text/xml; charset="{encoding}"'.format(
                    encoding=self.ENCODING),
            'SOAPAction': '"{service_type}#GetProtocolInfo"'.format(
                service_type=self.service_connection.service_type),
        }
        data = self.xml['get_protocol_info'].format(
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
                'text/xml; charset="{encoding}"'.format(
                    encoding=self.ENCODING),
            'SOAPAction': '"{service_type}#Stop"'.format(
                service_type=self.service_transport.service_type),
        }
        data = self.xml['stop'].format(
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
                'text/xml; charset="{encoding}"'.format(
                    encoding=self.ENCODING),
            'SOAPAction': '"{service_type}#Pause"'.format(
                service_type=self.service_transport.service_type),
        }
        data = self.xml['pause'].format(
            encoding=self.ENCODING,
        )
        response = requests.post(
            url, data=data.encode(self.ENCODING), headers=headers)
        if response.status_code == 200:
            self.state = self.PAUSE
        self._debug('pause', url, headers, data, response)
        return response.status_code


class CoinedUpnpMediaRenderer(
        pulseaudio_dlna.plugins.renderer.CoinedBaseRendererMixin, UpnpMediaRenderer):

    def play(self):
        stream_url = self.get_stream_url()
        if UpnpMediaRenderer.register(self, stream_url) == 200:
            return UpnpMediaRenderer.play(self)
        else:
            logging.error('"{}" registering failed!'.format(self.name))


class UpnpMediaRendererFactory(object):

    ST_HEADER = 'urn:schemas-upnp-org:device:MediaRenderer:1'

    @classmethod
    def from_url(self, url, type_=UpnpMediaRenderer):
        try:
            response = requests.get(url)
            logging.debug('Response from UPNP device ({url})\n'
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
            logging.info(
                'No valid XML returned from {url}.'.format(url=url))
            return None

    @classmethod
    def from_header(self, header, type_=UpnpMediaRenderer):
        if header['location']:
            return self.from_url(header['location'], type_)
