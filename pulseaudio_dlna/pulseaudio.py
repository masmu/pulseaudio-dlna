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

import sys
import dbus
import os
import subprocess
import logging
import functools
import upnp.renderer


class PulseAudio(object):
    def __init__(self):
        self.streams = []
        self.sinks = []

    def _connect(self, signals):
        self.bus = self._get_bus()
        self.core = self.bus.get_object(object_path='/org/pulseaudio/core1')
        for sig_name, interface, sig_handler in signals:
            self.bus.add_signal_receiver(sig_handler, sig_name)
            self.core.ListenForSignal(
                interface.format(sig_name), dbus.Array(signature='o'))

    def _get_bus_address(self):
        server_address = os.environ.get('PULSE_DBUS_SERVER', None)
        if server_address is None and \
           os.access('/run/pulse/dbus-socket', os.R_OK | os.W_OK):
            server_address = 'unix:path=/run/pulse/dbus-socket'
        if server_address is None:
            lookup_object = dbus.SessionBus().get_object(
                'org.PulseAudio1', '/org/pulseaudio/server_lookup1')
            server_address = lookup_object.Get(
                'org.PulseAudio.ServerLookup1',
                'Address',
                dbus_interface='org.freedesktop.DBus.Properties')
        return server_address

    def _get_bus(self):
        try:
            server_address = self._get_bus_address()
            return dbus.connection.Connection(server_address)
        except dbus.exceptions.DBusException:
            subprocess.Popen(
                ['pactl', 'load-module', 'module-dbus-protocol'],
                stdout=subprocess.PIPE).communicate()
            try:
                server_address = self._get_bus_address()
                return dbus.connection.Connection(server_address)
            except dbus.exceptions.DBusException:
                logging.error('PulseAudio seems not to be running or pulseaudio '
                              'dbus module could not be loaded.')
                sys.exit(1)

    def update(self):
        self.update_playback_streams()
        self.update_sinks()

        for stream in self.streams:
            for sink in self.sinks:
                if sink.object_path == stream.device:
                    sink.streams.append(stream)

    def update_playback_streams(self):
        stream_paths = self.core.Get(
            'org.PulseAudio.Core1', 'PlaybackStreams',
            dbus_interface='org.freedesktop.DBus.Properties')

        self.streams = []
        for stream_path in stream_paths:
            obj = self.bus.get_object(object_path=stream_path)
            stream = PulseStream(
                object_path=str(stream_path),
                index=str(obj.Get('org.PulseAudio.Core1.Stream', 'Index')),
                device=str(obj.Get('org.PulseAudio.Core1.Stream', 'Device')),
            )
            self.streams.append(stream)

    def update_sinks(self):
        sink_paths = self.core.Get(
            'org.PulseAudio.Core1', 'Sinks',
            dbus_interface='org.freedesktop.DBus.Properties')

        self.sinks = []
        for sink_path in sink_paths:
            obj = self.bus.get_object(object_path=sink_path)
            sink = PulseSink(
                object_path=str(sink_path),
                index=str(obj.Get('org.PulseAudio.Core1.Device', 'Index')),
                name=str(obj.Get('org.PulseAudio.Core1.Device', 'Name')),
            )
            self.sinks.append(sink)

    def create_null_sink(self, sink_name, sink_description):
        cmd = [
            'pactl',
            'load-module',
            'module-null-sink',
            'sink_name="{}"'.format(sink_name),
            'sink_properties=device.description="{}"'.format(
                sink_description.replace(' ', '\ ')
            ),
        ]
        entity_id = int(subprocess.check_output(cmd))
        if entity_id > 0:
            self.update_sinks()
            for sink in self.sinks:
                if sink.name == sink_name:
                    sink.entity = entity_id  # ugly hack
                    return sink

    def delete_null_sink(self, id):
        cmd = [
            'pactl',
            'unload-module',
            str(id),
        ]
        subprocess.check_output(cmd)


@functools.total_ordering
class PulseSink(object):

    __shared_state = {}

    def __init__(self, object_path, index, name):
        if object_path not in self.__shared_state:
            self.__shared_state[object_path] = {}
        self.__dict__ = self.__shared_state[object_path]

        self.object_path = object_path
        self.index = index
        self.name = name

        if hasattr(self, 'entity') is False:
            self.entity = None

        self.monitor = self.name + '.monitor'
        self.streams = []

    def __eq__(self, other):
        return self.object_path == other.object_path

    def __gt__(self, other):
        return self.object_path > other.object_path

    def __str__(self):
        string = '<PulseSink path="{}" name="{}" entity="{}">\n'.format(
            self.object_path,
            self.name,
            self.entity,
        )
        if len(self.streams) == 0:
            string = string + '        -- no streams --'
        else:
            for stream in self.streams:
                string = string + '        {}\n'.format(stream)
        return string


@functools.total_ordering
class PulseStream(object):

    __shared_state = {}

    def __init__(self, object_path, index, device):
        if object_path not in self.__shared_state:
            self.__shared_state[object_path] = {}
        self.__dict__ = self.__shared_state[object_path]

        self.object_path = object_path
        self.index = index
        self.device = device

    def __eq__(self, other):
        return self.object_path == other.object_path

    def __gt__(self, other):
        return self.object_path > other.object_path

    def __str__(self):
        return '<PulseStream path="{}" device="{}">'.format(
            self.object_path,
            self.device,
        )


class PulseUpnpBridge(object):
    def __init__(self, sink, upnp_device):
        self.sink = sink
        self.upnp_device = upnp_device

    def __cmp__(self, other):
        if isinstance(other, PulseUpnpBridge):
            return (self.upnp_device == other.upnp_device and
                    self.sink == other.sink)
        if isinstance(other, upnp.renderer.UpnpMediaRenderer):
            return self.upnp_device == other

    def __str__(self):
        return "<Bridge>\n    {}\n    {}\n".format(self.sink, self.upnp_device)


class PulseWatcher(PulseAudio):
    def __init__(self):
        PulseAudio.__init__(self)

        self.bridges = []
        self.upnp_devices = []

        signals = (
            ('NewPlaybackStream', 'org.PulseAudio.Core1.{}',
                self.on_new_playback_stream),
            ('PlaybackStreamRemoved', 'org.PulseAudio.Core1.{}',
                self.on_playback_stream_removed),
            ('DeviceUpdated', 'org.PulseAudio.Core1.Stream.{}',
                self.on_device_updated),
        )
        self._connect(signals)
        self.update()

    def set_upnp_devices(self, upnp_devices):
        self.upnp_devices = upnp_devices
        for upnp_device in upnp_devices:
            self._ensure_bridge(upnp_device)

    def _ensure_bridge(self, upnp_device):
        if upnp_device not in self.bridges:
            sink = self.create_null_sink(
                upnp_device.short_name, upnp_device.name)
            self.bridges.append(PulseUpnpBridge(sink, upnp_device))

    def cleanup(self):
        for bridge in self.bridges:
            logging.info('remove "{}" sink ...'.format(bridge.sink))
            self.delete_null_sink(bridge.sink.entity)

    def on_device_updated(self, sink_path):
        logging.info('PulseWatcher.on_device_updated "{path}"'.format(
            path=sink_path))
        self.update()
        self._handle_sink_update(sink_path)

    def on_new_playback_stream(self, stream_path):
        logging.info('PulseWatcher.on_new_playback_stream "{path}"'.format(
            path=stream_path))
        self.update()
        for sink in self.sinks:
            for stream in sink.streams:
                if stream.object_path == stream_path:
                    self._handle_sink_update(sink.object_path)
                    return

    def on_playback_stream_removed(self, stream_path):
        logging.info('PulseWatcher.on_playback_stream_removed "{path}"'.format(
            path=stream_path))
        for sink in self.sinks:
            for stream in sink.streams:
                if stream.object_path == stream_path:
                    self.update()
                    self._handle_sink_update(sink.object_path)
                    return

    def _handle_sink_update(self, sink_path):
        for bridge in self.bridges:
            if bridge.upnp_device.state == bridge.upnp_device.PLAYING:
                if len(bridge.sink.streams) == 0:
                    if bridge.upnp_device.stop() == 200:
                        logging.info('"{}" was stopped.'.format(
                            bridge.upnp_device.name))
                    else:
                        logging.error('"{}" stopping failed!'.format(
                            bridge.upnp_device.name))
                    continue
            if bridge.sink.object_path == sink_path:
                if bridge.upnp_device.state == bridge.upnp_device.IDLE:
                    if bridge.upnp_device.register() == 200:
                        logging.info('"{}" registered.'.format(
                            bridge.upnp_device.name))
                    else:
                        logging.error('"{}" registering failed!'.format(
                            bridge.upnp_device.name))
                if bridge.upnp_device.state == bridge.upnp_device.IDLE or \
                   bridge.upnp_device.state == bridge.upnp_device.PAUSE:
                    if bridge.upnp_device.play() == 200:
                        logging.info('"{}" is playing.'.format(
                            bridge.upnp_device.name))
                    else:
                        logging.error('"{}" playing failed!'.format(
                            bridge.upnp_device.name))
