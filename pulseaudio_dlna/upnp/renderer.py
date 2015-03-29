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
import functools
import random
import BeautifulSoup
import pulseaudio_dlna.pulseaudio


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
        self.services = services
        self.state = self.IDLE

    def _short_name(self, name):
        return re.sub(r'[^a-z0-9]', '', name.lower())

    def _get_av_transport(self):
        for service in self.services:
            if service['service_type'].startswith(
                    'urn:schemas-upnp-org:service:AVTransport:'):
                return service

    def _get_av_transport_url(self):
        av_transport = self._get_av_transport()
        return self._get_url(av_transport['control_url'])

    def _get_url(self, control_url):
        host = 'http://{ip}:{port}'.format(
            ip=self.ip,
            port=self.port,
        )
        return urlparse.urljoin(host, control_url)

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
        url = self._get_av_transport_url()
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(encoding=self.ENCODING),
            'SOAPAction': '"urn:schemas-upnp-org:service:AVTransport:1#SetAVTransportURI"',
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

    def play(self):
        url = self._get_av_transport_url()
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(encoding=self.ENCODING),
            'SOAPAction': '"urn:schemas-upnp-org:service:AVTransport:1#Play"',
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
        url = self._get_av_transport_url()
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(encoding=self.ENCODING),
            'SOAPAction': '"urn:schemas-upnp-org:service:AVTransport:1#Stop"',
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
        url = self._get_av_transport_url()
        headers = {
            'Content-Type':
                'text/xml; charset="{encoding}"'.format(encoding=self.ENCODING),
            'SOAPAction': '"urn:schemas-upnp-org:service:AVTransport:1#Stop"',
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
        return '<UpnpMediaRenderer name="{}" short_name="{}" state="{}">'.format(
            self.name,
            self.short_name,
            self.state,
        )


class CoinedUpnpMediaRenderer(UpnpMediaRenderer):
    def __init__(self, *args):
        UpnpMediaRenderer.__init__(self, *args)
        self.server_url = None
        self.stream_url = None

    def set_server_url(self, server_url):
        self.server_url = server_url
        self.stream_name = '/{stream_name}.mp3'.format(
            stream_name=self.short_name,
        )
        self.stream_url = urlparse.urljoin(self.server_url, self.stream_name)
        logging.debug('setting stream url for {device_name} to "{url}"'.format(
            device_name=self.name,
            url=self.stream_url))

    def register(self):
        return UpnpMediaRenderer.register(self, self.stream_url)

    def __str__(self):
        return '<CoinedUpnpMediaRenderer name="{}" short_name="{}" state="{}">'.format(
            self.name,
            self.short_name,
            self.state,
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
