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

import re
import cgi
import requests
import urlparse
import socket
import functools
import BeautifulSoup
import pulseaudio


@functools.total_ordering
class UpnpMediaRenderer(object):

    REGISTER_XML = """<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <u:SetAVTransportURI xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
            <InstanceID>0</InstanceID>
            <CurrentURI>{stream_url}</CurrentURI>
            <CurrentURIMetaData>{current_url_metadata}</CurrentURIMetaData>
        </u:SetAVTransportURI>
    </s:Body>
</s:Envelope>"""

    REGISTER_XML_METADATA = """<?xml version="1.0" encoding="UTF-8"?>
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

    PLAY_XML = """<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <u:Play xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
            <InstanceID>0</InstanceID>
            <Speed>1</Speed>
        </u:Play>
    </s:Body>
</s:Envelope>
"""

    STOP_XML = """<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <u:Stop xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
            <InstanceID>0</InstanceID>
            <Speed>1</Speed>
        </u:Stop>
    </s:Body>
</s:Envelope>"""

    PAUSE_XML = """<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<s:Envelope s:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/" xmlns:s="http://schemas.xmlsoap.org/soap/envelope/">
    <s:Body>
        <u:Pause xmlns:u="urn:schemas-upnp-org:service:AVTransport:1">
            <InstanceID>0</InstanceID>
            <Speed>1</Speed>
        </u:Pause>
    </s:Body>
</s:Envelope>"""

    PLAYING = 'playing'
    IDLE = 'idle'
    PAUSE = 'paused'

    def __init__(self, name, ip, port, udn, services):
        self.name = name
        self.short_name = self._short_name(name)
        self.ip = ip
        self.port = port
        self.udn = udn
        self.services = services
        self.state = self.IDLE

    def _short_name(self, name):
        return re.sub(r'[^a-z]', '', name.lower())

    def _get_av_transport(self):
        for service in self.services:
            if (service['service_type'] ==
               'urn:schemas-upnp-org:service:AVTransport:1'):
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

    def register(self, stream_url):
        url = self._get_av_transport_url()
        headers = {
            'Content-Type': 'text/xml',
            'SOAPAction': '"urn:schemas-upnp-org:service:AVTransport:1#SetAVTransportURI"',
        }
        metadata = self.REGISTER_XML_METADATA.format(
            stream_url=stream_url,
            title='Live Audio',
            artist='PulseAudio on {}'.format(socket.gethostname()),
            creator='PulseAudio',
            album='Stream',
        )
        data = self.REGISTER_XML.format(
            stream_url=stream_url,
            current_url_metadata=cgi.escape(metadata),
        )
        response = requests.post(url, data=data, headers=headers)
        return response.status_code

    def play(self):
        url = self._get_av_transport_url()
        headers = {
            'Content-Type': 'text/xml',
            'SOAPAction': '"urn:schemas-upnp-org:service:AVTransport:1#Play"',
        }
        response = requests.post(url, data=self.PLAY_XML, headers=headers)
        if response.status_code == 200:
            self.state = self.PLAYING
        return response.status_code

    def stop(self):
        url = self._get_av_transport_url()
        headers = {
            'Content-Type': 'text/xml',
            'SOAPAction': '"urn:schemas-upnp-org:service:AVTransport:1#Stop"',
        }
        response = requests.post(url, data=self.STOP_XML, headers=headers)
        if response.status_code == 200:
            self.state = self.IDLE
        return response.status_code

    def pause(self):
        url = self._get_av_transport_url()
        headers = {
            'Content-Type': 'text/xml',
            'SOAPAction': '"urn:schemas-upnp-org:service:AVTransport:1#Stop"',
        }
        response = requests.post(url, data=self.PAUSE_XML, headers=headers)
        if response.status_code == 200:
            self.state = self.PAUSE
        return response.status_code

    def __eq__(self, other):
        if isinstance(other, UpnpMediaRenderer):
            return self.name == other.name
        if isinstance(other, pulseaudio.PulseUpnpBridge):
            return self.name == other.upnp_device.name

    def __gt__(self, other):
        if isinstance(other, UpnpMediaRenderer):
            return self.name > other.name
        if isinstance(other, pulseaudio.PulseUpnpBridge):
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
        self.stream_name = '/{stream_name}.stream'.format(
            stream_name=self.short_name,
        )
        self.stream_url = urlparse.urljoin(self.server_url, self.stream_name)

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
    def from_header(self, header, type_=UpnpMediaRenderer):
        header = re.findall(r"(?P<name>.*?): (?P<value>.*?)\r\n", header)
        header = {k.lower(): v for k, v in dict(header).items()}
        if header['location']:
            location = header['location']
            url_object = urlparse.urlparse(location)
            ip, port = url_object.netloc.split(':')
            response = requests.get(location)
            soup = BeautifulSoup.BeautifulSoup(response.text)
            services = []
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
