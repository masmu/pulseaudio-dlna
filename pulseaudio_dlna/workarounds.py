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

import logging
from lxml import etree
import requests
import urllib.parse
import traceback


logger = logging.getLogger('pulseaudio_dlna.workarounds')


class BaseWorkaround(object):
    """
    Define functions which are called at specific situations during the
    application.

    Those may be:
        - before_register
        - after_register
        - before_play
        - after_play
        - before_stop
        - after_stop

    This may be extended in the future.
    """

    ENABLED = True

    def __init__(self):
        pass

    def run(self, method_name, *args, **kwargs):
        method = getattr(self, method_name, None)
        if self.ENABLED and method and callable(method):
            logger.info('Running workaround "{}".'.format(method_name))
            method(*args, **kwargs)


class YamahaWorkaround(BaseWorkaround):
    # Misc constants
    REQUEST_TIMEOUT = 5
    ENCODING = 'utf-8'
    URL_FORMAT = 'http://{ip}:{port}{url}'

    # MediaRenderer constants
    MR_YAMAHA_PREFIX = 'yamaha'
    MR_YAMAHA_DEVICE = MR_YAMAHA_PREFIX + ':' + 'X_device'
    MR_YAMAHA_URLBASE = MR_YAMAHA_PREFIX + ':' + 'X_URLBase'
    MR_YAMAHA_SERVICELIST = MR_YAMAHA_PREFIX + ':' + 'X_serviceList'
    MR_YAMAHA_SERVICE = MR_YAMAHA_PREFIX + ':' + 'X_service'
    MR_YAMAHA_CONTROLURL = MR_YAMAHA_PREFIX + ':' + 'X_controlURL'

    MR_YAMAHA_URLBASE_PATH = '/'.join([MR_YAMAHA_DEVICE, MR_YAMAHA_URLBASE])
    MR_YAMAHA_CONTROLURL_PATH = '/'.join(
        [MR_YAMAHA_DEVICE, MR_YAMAHA_SERVICELIST, MR_YAMAHA_SERVICE,
         MR_YAMAHA_CONTROLURL])

    # YamahaRemoteControl constants
    YRC_TAG_ROOT = 'YAMAHA_AV'
    YRC_KEY_RC = 'RC'
    YRC_CMD_GETPARAM = 'GetParam'
    YRC_BASEPATH_CONFIG = 'Config'
    YRC_BASEPATH_BASICSTATUS = 'Basic_Status'
    YRC_BASEPATH_FEATURES = 'Feature_Existence'
    YRC_BASEPATH_INPUTNAMES = 'Name/Input'
    YRC_BASEPATH_POWER = 'Power_Control/Power'
    YRC_BASEPATH_SOURCE = 'Input/Input_Sel'
    YRC_VALUE_POWER_ON = 'On'
    YRC_VALUE_POWER_OFF = 'Standby'

    YRC_REQUEST_CONTENTTYPE = 'text/xml; charset="{encoding}"'.format(
        encoding=ENCODING)
    YRC_REQUEST_TEMPLATE = \
        '<?xml version="1.0" encoding="{encoding}"?>' \
        '<YAMAHA_AV cmd="{cmd}">{request}</YAMAHA_AV>'

    # Known server modes
    YRC_SERVER_MODES = ['SERVER', 'PC']

    def __init__(self, xml):
        BaseWorkaround.__init__(self)
        self.enabled = False

        self.control_url = None
        self.ip = None
        self.port = None

        self.zones = None
        self.sources = None

        self.server_mode_zone = None
        self.server_mode_source = None

        try:
            # Initialize YamahaRemoteControl interface
            if (not self._detect_remotecontrolinterface(xml)):
                raise Exception()
            self.enabled = True
        except Exception:
            logger.warning(
                'The YamahaWorkaround initialization failed. '
                'Automatic source switching will not be enabled'
                ' - Please switch to server mode manually to enable UPnP'
                ' streaming')
            logger.debug(traceback.format_exc())

    def _detect_remotecontrolinterface(self, xml):
        # Check for YamahaRemoteControl support
        if (not self._parse_xml(xml)):
            logger.info('No Yamaha RemoteControl interface detected')
            return False
        logger.info('Yamaha RemoteControl found: ' + self.URL_FORMAT.format(
            ip=self.ip, port=self.port, url=self.control_url))
        # Get supported features
        self.zones, self.sources = self._query_supported_features()
        if ((self.zones is None) or (self.sources is None)):
            logger.error('Failed to query features')
            return False
        # Determine main zone
        logger.info('Supported zones: ' + ', '.join(self.zones))
        self.server_mode_zone = self.zones[0]
        logger.info('Using \'{zone}\' as main zone'.format(
            zone=self.server_mode_zone
        ))
        # Determine UPnP server source
        if (self.sources):
            logger.info('Supported sources: ' + ', '.join(self.sources))
            for source in self.YRC_SERVER_MODES:
                if (source not in self.sources):
                    continue
                self.server_mode_source = source
                break
        else:
            logger.warning('Querying supported features failed')
        if (not self.server_mode_source):
            logger.warning('Unable to determine UPnP server mode source')
            return False
        logger.info('Using \'{source}\' as UPnP server mode source'.format(
            source=self.server_mode_source
        ))
        return True

    def _parse_xml(self, xml):
        # Parse MediaRenderer description XML
        xml_root = etree.fromstring(xml)
        namespaces = xml_root.nsmap
        namespaces.pop(None, None)

        # Determine AVRC URL
        url_base = xml_root.find(self.MR_YAMAHA_URLBASE_PATH, namespaces)
        control_url = xml_root.find(self.MR_YAMAHA_CONTROLURL_PATH, namespaces)
        if ((url_base is None) or (control_url is None)):
            return False
        ip, port = urllib.parse.urlparse(url_base.text).netloc.split(':')
        if ((not ip) or (not port)):
            return False

        self.ip = ip
        self.port = port
        self.control_url = control_url.text
        return True

    def _generate_request(self, cmd, root, path, value):
        # Generate headers
        headers = {
            'Content-Type': self.YRC_REQUEST_CONTENTTYPE,
        }
        # Generate XML request
        tags = path.split('/')
        if (root):
            tags = [root] + tags
        request = ''
        for tag in tags:
            request += '<{tag}>'.format(tag=tag)
        request += value
        for tag in reversed(tags):
            request += '</{tag}>'.format(tag=tag)
        body = self.YRC_REQUEST_TEMPLATE.format(
            encoding=self.ENCODING,
            cmd=cmd,
            request=request,
        )
        # Construct URL
        url = self.URL_FORMAT.format(
            ip=self.ip,
            port=self.port,
            url=self.control_url,
        )
        return headers, body, url

    def _get(self, root, path, value, filter_path=None):
        # Generate request
        headers, data, url = self._generate_request('GET', root, path, value)
        # POST request
        try:
            logger.debug('Yamaha RC request: '+data)
            response = requests.post(
                url, data.encode(self.ENCODING),
                headers=headers, timeout=self.REQUEST_TIMEOUT)
            logger.debug('Yamaha RC response: ' + response.text)
            if response.status_code != 200:
                logger.error(
                    'Yamaha RC request failed - Status code: {code}'.format(
                        code=response.status_code))
                return None
        except requests.exceptions.Timeout:
            logger.error('Yamaha RC request failed - Connection timeout')
            return None
        # Parse response
        xml_root = etree.fromstring(response.content)
        if (xml_root.tag != self.YRC_TAG_ROOT):
            logger.error("Malformed response: Root tag missing")
            return None
        # Parse response code
        rc = xml_root.get(self.YRC_KEY_RC)
        if (not rc):
            logger.error("Malformed response: RC attribute missing")
            return None
        rc = int(rc)
        if (rc > 0):
            logger.error(
                'Yamaha RC request failed - Response code: {code}'.format(
                    code=rc))
            return rc
        # Only return subtree
        result_path = []
        if (root):
            result_path.append(root)
        result_path.append(path)
        if (filter_path):
            result_path.append(filter_path)
        result_path = '/'.join(result_path)
        return xml_root.find(result_path)

    def _put(self, root, path, value):
        # Generate request
        headers, data, url = self._generate_request('PUT', root, path, value)
        # POST request
        try:
            logger.debug('Yamaha RC request: '+data)
            response = requests.post(
                url, data.encode(self.ENCODING),
                headers=headers, timeout=self.REQUEST_TIMEOUT)
            logger.debug('Yamaha RC response: ' + response.text)
            if response.status_code != 200:
                logger.error(
                    'Yamaha RC request failed - Status code: {code}'.format(
                        code=response.status_code))
                return False
        except requests.exceptions.Timeout:
            logger.error('Yamaha RC request failed - Connection timeout')
            return None
        # Parse response
        xml_root = etree.fromstring(response.content)
        if (xml_root.tag != self.YRC_TAG_ROOT):
            logger.error("Malformed response: Root tag missing")
            return None
        # Parse response code
        rc = xml_root.get(self.YRC_KEY_RC)
        if (not rc):
            logger.error("Malformed response: RC attribute missing")
            return None
        rc = int(rc)
        if (rc > 0):
            logger.error(
                'Yamaha RC request failed - Response code: {code}'.format(
                    code=rc))
            return rc
        return 0

    def _query_supported_features(self):
        xml_response = self._get('System', 'Config', self.YRC_CMD_GETPARAM)
        if (xml_response is None):
            return None, None

        xml_features = xml_response.find(self.YRC_BASEPATH_FEATURES)
        if (xml_features is None):
            logger.debug('Failed to find feature description')
            return None, None

        # Features can be retrieved in different ways, most probably
        # dependending on the recever's firmware / protocol version
        # Here are the different responses known up to now:
        #
        # 1. Comma-separated list of all features in one single tag, containing
        #    all input sources
        # 2. Each feature is enclosed by a tag along with context information
        #    depending on the XML path:
        #    - YRC_BASEPATH_FEATURES: availability and/or support
        #      (0 == not supported, 1 == supported)
        #    - YRC_BASEPATH_INPUTNAMES: input/source name
        #    Every feature is a input source, if it does not contain the
        #    substring 'Zone'. Otherwise, it is a zone supported by the
        #    receiver.
        zones = []
        sources = []
        if (xml_features.text):
            # Format 1:
            sources = xml_features.text.split(',')
        else:
            # Format 2:
            for child in xml_features.getchildren():
                if ((not child.text) or (int(child.text) == 0)):
                    continue
                if ('Zone' in child.tag):
                    zones.append(child.tag)
                else:
                    sources.append(child.tag)
            xml_names = xml_response.find(self.YRC_BASEPATH_INPUTNAMES)
            if (xml_names is not None):
                for child in xml_names.getchildren():
                    sources.append(child.tag)

        # If we got no zones up to now, we have to assume, that the receiver
        # has no multi zone support. Thus there can be only one!
        # Let's call it "System" and pray for the best!
        if (len(zones) == 0):
            zones.append('System')

        return zones, sources

    def _set_source(self, value, zone=None):
        if (not zone):
            zone = self.server_mode_zone
        self._put(zone, self.YRC_BASEPATH_SOURCE, value)

    def before_register(self):
        if (not self.enabled):
            return
        logger.info('Switching to UPnP server mode')
        self._set_source(self.server_mode_source)
