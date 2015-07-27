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


class BaseCommand(object):
    def __init__(self):
        self._sender_id = None
        self._destination_id = None
        self._namespace = None
        self._data = None

    @property
    def sender_id(self):
        return self._sender_id

    @sender_id.setter
    def sender_id(self, value):
        self._sender_id = value

    @property
    def destination_id(self):
        return self._destination_id

    @destination_id.setter
    def destination_id(self, value):
        self._destination_id = value

    @property
    def request_id(self):
        if 'requestId' in self.data:
            return self.data['requestId']
        return 0

    @request_id.setter
    def request_id(self, value):
        if value is not None:
            self.data['requestId'] = value

    @property
    def session_id(self):
        if 'sessionId' in self.data:
            return self.data['sessionId']
        return None

    @session_id.setter
    def session_id(self, value):
        if value is not None:
            self.data['sessionId'] = value

    @property
    def namespace(self):
        return self._namespace

    @namespace.setter
    def namespace(self, value):
        self._namespace = value

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    def __str__(self):
        return ('<{class_name}>\n'
                '  namespace: {namespace}\n'
                '  destination_id: {destination_id}\n'
                '  data: {data}'.format(
                    class_name=self.__class__.__name__,
                    namespace=self.namespace,
                    destination_id=self.destination_id,
                    data=self.data))


class ConnectCommand(BaseCommand):
    def __init__(self, destination_id=None, namespace=None, agent=None):
        BaseCommand.__init__(self)
        self.data = {
            'origin': {},
            'type': 'CONNECT',
            'userAgent': agent or 'Unknown'
        }
        self.destination_id = destination_id
        self.namespace = (namespace or
                          'urn:x-cast:com.google.cast.tp.connection')


class CloseCommand(BaseCommand):
    def __init__(self, destination_id=None, namespace=None):
        BaseCommand.__init__(self)
        self.data = {
            'origin': {},
            'type': 'CLOSE'
        }
        self.destination_id = destination_id
        self.namespace = (namespace or
                          'urn:x-cast:com.google.cast.tp.connection')


class StatusCommand(BaseCommand):
    def __init__(self, destination_id=None, namespace=None):
        BaseCommand.__init__(self)
        self.data = {
            'type': 'GET_STATUS'
        }
        self.request_id = False
        self.destination_id = destination_id
        self.namespace = namespace or 'urn:x-cast:com.google.cast.receiver'


class LaunchCommand(BaseCommand):
    def __init__(self, app_id, destination_id=None, namespace=None):
        BaseCommand.__init__(self)
        self.data = {
            'appId': app_id,
            'type': 'LAUNCH'
        }
        self.request_id = False
        self.destination_id = destination_id
        self.namespace = namespace or 'urn:x-cast:com.google.cast.receiver'


class StopCommand(BaseCommand):
    def __init__(self, session_id=False, destination_id=None,
                 namespace=None):
        BaseCommand.__init__(self)
        self.data = {
            'type': 'STOP'
        }
        self.session_id = False
        self.request_id = False
        self.destination_id = destination_id
        self.namespace = namespace or 'urn:x-cast:com.google.cast.receiver'


class PongCommand(BaseCommand):
    def __init__(self, session_id=False, destination_id=None,
                 namespace=None):
        BaseCommand.__init__(self)
        self.data = {
            'type': 'PONG'
        }
        self.session_id = False
        self.request_id = False
        self.destination_id = destination_id
        self.namespace = namespace or 'urn:x-cast:com.google.cast.tp.heartbeat'
