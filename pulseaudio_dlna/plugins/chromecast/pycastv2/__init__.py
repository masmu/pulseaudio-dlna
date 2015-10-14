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

import time
import logging

import commands
import cast_socket

logger = logging.getLogger('pycastv2')


class ChannelClosedException(Exception):
    pass


class TimeoutException(Exception):
    pass


class ChannelController(object):
    def __init__(self, socket):
        self.request_id = 1
        self.transport_id = 'receiver-0'
        self.session_id = None
        self.app_id = None

        self.channels = []

        self.socket = socket
        self.socket.add_send_listener(self._handle_send)
        self.socket.add_read_listener(self._handle_response)
        self.socket.send_and_wait(commands.StatusCommand())

    def _get_unused_request_id(self):
        self.request_id += 1
        return self.request_id - 1

    def _handle_send(self, command):
        if command.request_id is not None:
            command.request_id = (command.request_id or
                                  self._get_unused_request_id())
        if command.session_id is not None:
            command.session_id = command.session_id or self.session_id
        command.sender_id = command.sender_id or 'sender-0'
        if command.destination_id is None:
            command.destination_id = 'receiver-0'
        else:
            command.destination_id = (command.destination_id or
                                      self.transport_id)
        if not self.is_channel_connected(command.destination_id):
            self.connect_channel(command.destination_id)
        return command

    def _handle_response(self, response):
        if 'type' in response:
            response_type = response['type']
            if response_type == 'RECEIVER_STATUS':
                if 'applications' in response['status']:
                    applications = response['status']['applications'][0]
                    self.transport_id = (
                        applications.get('transportId') or self.transport_id)
                    self.session_id = (
                        applications.get('sessionId') or self.session_id)
                    self.app_id = (
                        applications.get('appId') or self.app_id)
                else:
                    self.transport_id = 'receiver-0'
                    self.session_id = None
                    self.app_id = None
            elif response_type == 'PING':
                self.socket.send(commands.PongCommand())
            elif response_type == 'CLOSE':
                raise ChannelClosedException()

    def is_channel_connected(self, destination_id):
        return destination_id in self.channels

    def connect_channel(self, destination_id):
        self.channels.append(destination_id)
        self.socket.send(commands.ConnectCommand(destination_id))

    def disconnect_channel(self, destination_id):
        self.socket.send(commands.CloseCommand(destination_id))
        self.channels.remove(destination_id)

    def __str__(self):
        return ('<ChannelController>\n'
                '  request_id: {request_id}\n'
                '  transport_id: {transport_id}\n'
                '  session_id: {session_id}\n'
                '  app_id: {app_id}'.format(
                    request_id=self.request_id,
                    transport_id=self.transport_id,
                    session_id=self.session_id,
                    app_id=self.app_id))


class ChromecastController():

    APP_BACKDROP = 'E8C28D3C'
    WAIT_INTERVAL = 0.1

    def __init__(self, ip, timeout=10):
        self.timeout = timeout
        self.socket = cast_socket.CastSocket(ip)
        self.channel_controller = ChannelController(self.socket)

    def is_app_running(self, app_id):
        return self.channel_controller.app_id == app_id

    def launch_application(self, app_id):
        if not self.is_app_running(app_id):
            self.socket.send(commands.LaunchCommand(app_id))
            start_time = time.time()
            while not self.is_app_running(app_id):
                self.socket.send_and_wait(commands.StatusCommand())
                current_time = time.time()
                if current_time - start_time > self.timeout:
                    raise TimeoutException()
                time.sleep(self.WAIT_INTERVAL)
        else:
            logger.debug('Starting not necessary. Application is running ...')

    def stop_application(self):
        if not self.is_app_running(self.APP_BACKDROP):
            self.socket.send(commands.StopCommand())
            start_time = time.time()
            while not self.is_app_running(self.APP_BACKDROP):
                self.socket.send_and_wait(commands.StatusCommand())
                current_time = time.time()
                if current_time - start_time > self.timeout:
                    raise TimeoutException()
                time.sleep(self.WAIT_INTERVAL)
        else:
            logger.debug('Stop not necessary. Backdrop is running ...')

    def disconnect_application(self):
        if not self.is_app_running(self.APP_BACKDROP):
            self.socket.send(commands.CloseCommand(destination_id=False))
            start_time = time.time()
            while self.is_app_running(self.APP_BACKDROP):
                self.socket.send_and_wait(commands.StatusCommand())
                current_time = time.time()
                if current_time - start_time > self.timeout:
                    raise TimeoutException()
                time.sleep(self.WAIT_INTERVAL)
        else:
            logger.debug('Closing not necessary. Backdrop is running ...')

    def wait(self, timeout):
        self.socket.wait(timeout)

    def cleanup(self):
        self.socket.close()


class LoadCommand(commands.BaseCommand):
    def __init__(self, url, mime_type, title=None, thumb=None,
                 session_id=None, destination_id=None, namespace=None):
        commands.BaseCommand.__init__(self)
        custom_data = {}
        if title or thumb:
            custom_data = {
                'payload': {
                    'title': title,
                    'thumb': thumb,
                }
            }
        self.data = {
            'autoplay': True,
            'currentTime': 0,
            'customData': custom_data,
            'media': {'contentId': url,
                      'contentType': mime_type,
                      'streamType': 'BUFFERED'},
            'type': 'LOAD'
        }
        self.request_id = False
        self.session_id = False
        self.destination_id = destination_id
        self.namespace = namespace or 'urn:x-cast:com.google.cast.media'


class LoadFailedException(Exception):
    pass


class MediaPlayerController(ChromecastController):

    APP_MEDIA_PLAYER = 'CC1AD845'

    PLAYER_STATE_BUFFERING = 'BUFFERING'
    PLAYER_STATE_PLAYING = 'PLAYING'
    PLAYER_STATE_PAUSED = 'PAUSED'
    PLAYER_STATE_IDLE = 'IDLE'

    def __init__(self, ip, timeout=10):
        ChromecastController.__init__(self, ip, timeout)
        self.media_session_id = None
        self.current_time = None
        self.media = None
        self.playback_rate = None
        self.volume = None
        self.player_state = None

        self.socket.add_read_listener(self._handle_response)

    def launch(self):
        self.launch_application(self.APP_MEDIA_PLAYER)

    def load(self, url, mime_type, title=None, thumb=None):
        self.launch()
        try:
            self.socket.send_and_wait(
                LoadCommand(
                    url, mime_type, title, thumb, destination_id=False))
            return True
        except (cast_socket.NoResponseException, LoadFailedException):
            return False

    def _update_attribute(self, name, value):
        if value is not None:
            setattr(self, name, value)

    def _handle_response(self, response):
        if 'type' in response:
            if response['type'] == 'MEDIA_STATUS':
                logger.debug('Recieved media status ...')
                status = response['status'][0]
                self._update_attribute(
                    'media_session_id', status.get('mediaSessionId', None))
                self._update_attribute(
                    'current_time', status.get('currentTime', None))
                self._update_attribute(
                    'media', status.get('media', None))
                self._update_attribute(
                    'playback_rate', status.get('playbackRate', None))
                self._update_attribute(
                    'volume', status.get('volume', None))
                self._update_attribute(
                    'player_state', status.get('playerState', None))
            elif response['type'] == 'LOAD_FAILED':
                raise LoadFailedException()

    @property
    def player_state(self):
        return self.player_state

    @property
    def is_playing(self):
        return (self.player_state is not None and
                self.player_state == self.PLAYER_STATE_PLAYING)

    @property
    def is_paused(self):
        return (self.player_state is not None and
                self.player_state == self.PLAYER_STATE_PAUSED)

    @property
    def is_idle(self):
        return (self.player_state is not None and
                self.player_state == self.PLAYER_STATE_IDLE)
