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

import ssl
import socket
import logging
import struct
import json
import time
import traceback
import select

import cast_channel_pb2

logger = logging.getLogger('pycastv2.cast_socket')


class NoResponseException(Exception):
    pass


class BaseChromecastSocket(object):
    def __init__(self, ip):
        self.sock = socket.socket()
        self.sock = ssl.wrap_socket(self.sock)
        self.sock.connect((ip, 8009))
        self.agent = 'chromecast_v2'

    def _generate_message(self,
                          source_id='sender-0', destination_id='receiver-0',
                          namespace=None):
        message = cast_channel_pb2.CastMessage()
        message.protocol_version = message.CASTV2_1_0
        message.source_id = source_id
        message.destination_id = destination_id
        message.payload_type = cast_channel_pb2.CastMessage.STRING
        if namespace:
            message.namespace = namespace
        return message

    def close(self):
        self.sock.close()
        logger.debug('Chromecast socket was cleaned up.')

    def send(self, data, sender_id, destination_id, namespace=None):
        json_data = json.dumps(data)
        message = self._generate_message(
            source_id=sender_id,
            destination_id=destination_id,
            namespace=namespace)
        message.payload_utf8 = json_data
        size = struct.pack('>I', message.ByteSize())
        formatted_message = size + message.SerializeToString()
        self.sock.sendall(formatted_message)

    def read(self):
        try:
            data = str('')
            while len(data) < 4:
                part = self.sock.recv(1)
                data += part
            length = struct.unpack('>I', data)[0]
            data = str('')
            while len(data) < length:
                part = self.sock.recv(2048)
                data += part
            message = self._generate_message()
            message.ParseFromString(data)
            response = json.loads(message.payload_utf8)
            return response
        except ssl.SSLError as e:
            if e.message == 'The read operation timed out':
                raise NoResponseException()
            else:
                logger.debug('Catched exception:')
                traceback.print_exc()
                return {}


class CastSocket(BaseChromecastSocket):
    def __init__(self, ip):
        BaseChromecastSocket.__init__(self, ip)
        self.read_listeners = []
        self.send_listeners = []
        self.response_cache = {}

    def send(self, command):
        for listener in self.send_listeners:
            command = listener(command)
        logger.debug('Sending message:\n{command}'.format(
            command=command))
        BaseChromecastSocket.send(
            self,
            data=command.data,
            sender_id=command.sender_id,
            destination_id=command.destination_id,
            namespace=command.namespace)
        return command.request_id

    def read(self, timeout=None):
        if timeout is not None:
            self.wait_for_read(timeout)
        response = BaseChromecastSocket.read(self)
        logger.debug('Recieved message:\n {message}'.format(
            message=json.dumps(response, indent=2)))
        for listener in self.read_listeners:
            listener(response)
        return response

    def add_read_listener(self, listener):
        self.read_listeners.append(listener)

    def add_send_listener(self, listener):
        self.send_listeners.append(listener)

    def send_and_wait(self, command):
        req_id = self.send(command)
        return self.wait_for_response_id(req_id)

    def wait_for_read(self, timeout=None):
        start_time = time.time()
        while True:
            if self._is_socket_readable():
                return
            current_time = time.time()
            if current_time - start_time > timeout:
                raise NoResponseException()
            time.sleep(0.1)

    def wait_for_response_id(self, req_id, timeout=10):
        start_time = time.time()
        while True:
            if not self._is_socket_readable():
                time.sleep(0.1)
            else:
                response = self.read()
                self._add_to_response_cache(response)
                if req_id in self.response_cache:
                    return response
            current_time = time.time()
            if current_time - start_time > timeout:
                raise NoResponseException()
        return None

    def wait_for_response_type(self, _type, timeout=10):
        start_time = time.time()
        while True:
            if not self._is_socket_readable():
                time.sleep(0.1)
            else:
                response = self.read()
                self._add_to_response_cache(response)
                if response.get('type', None) == _type:
                    return response
            current_time = time.time()
            if current_time - start_time > timeout:
                raise NoResponseException()
        return None

    def wait(self, timeout=10):
        start_time = time.time()
        while True:
            if not self._is_socket_readable():
                time.sleep(0.1)
            else:
                response = self.read()
                self._add_to_response_cache(response)
            current_time = time.time()
            if current_time - start_time > timeout:
                return
        return None

    def _add_to_response_cache(self, response):
        if 'requestId' in response:
            req_id = response['requestId']
            if int(req_id) != 0:
                self.response_cache[req_id] = response

    def _is_socket_readable(self):
        try:
            r, w, e = select.select([self.sock], [], [], 0)
            for sock in r:
                return True
        except socket.error:
            pass
        return False
