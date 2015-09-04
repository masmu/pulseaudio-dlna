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
import locale
import dbus
import os
import struct
import subprocess
import logging
import setproctitle
import gobject
import functools
import copy
import signal

import pulseaudio_dlna.plugins.renderer
import pulseaudio_dlna.notification

logger = logging.getLogger('pulseaudio_dlna.pulseaudio')


class PulseAudio(object):
    def __init__(self):
        self.streams = []
        self.sinks = []

        self.fallback_sink = None
        self.system_sinks = []

    def _connect(self, signals):
        self.bus = self._get_bus()
        self.core = self.bus.get_object(object_path='/org/pulseaudio/core1')
        for sig_name, interface, sig_handler in signals:
            self.bus.add_signal_receiver(sig_handler, sig_name)
            self.core.ListenForSignal(
                interface.format(sig_name), dbus.Array(signature='o'))

        try:
            fallback_sink_path = self.core.Get(
                'org.PulseAudio.Core1', 'FallbackSink',
                dbus_interface='org.freedesktop.DBus.Properties')
            self.fallback_sink = PulseSinkFactory.new(
                self.bus, fallback_sink_path)
        except:
            logger.info(
                'Could not get default sink. Perhaps there is no one set?')

        system_sink_paths = self.core.Get(
            'org.PulseAudio.Core1', 'Sinks',
            dbus_interface='org.freedesktop.DBus.Properties')
        for sink_path in system_sink_paths:
            sink = PulseSinkFactory.new(self.bus, sink_path)
            if sink:
                self.system_sinks.append(sink)

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
                logger.error('PulseAudio seems not to be running or PulseAudio'
                             ' dbus module could not be loaded.')
                sys.exit(1)

    def update(self):

        def retry_on_fail(method, tries=5):
            count = 1
            while not method():
                if count > tries:
                    return False
                count += 1
            return True

        if retry_on_fail(self.update_playback_streams) and \
           retry_on_fail(self.update_sinks):
            for stream in self.streams:
                for sink in self.sinks:
                    if sink.object_path == stream.device:
                        sink.streams.append(stream)
        else:
            logger.error(
                'Could not update sinks and streams. This normally indicates a '
                'problem with pulseaudio\'s dbus module. Try restarting '
                'pulseaudio if the problem persists.')

    def update_playback_streams(self):
        try:
            stream_paths = self.core.Get(
                'org.PulseAudio.Core1', 'PlaybackStreams',
                dbus_interface='org.freedesktop.DBus.Properties')

            self.streams = []
            for stream_path in stream_paths:
                stream = PulseStreamFactory.new(self.bus, stream_path)
                if stream:
                    self.streams.append(stream)
            return True
        except dbus.exceptions.DBusException:
            return False

    def update_sinks(self):
        try:
            sink_paths = self.core.Get(
                'org.PulseAudio.Core1', 'Sinks',
                dbus_interface='org.freedesktop.DBus.Properties')

            self.sinks = []
            for sink_path in sink_paths:
                sink = PulseSinkFactory.new(self.bus, sink_path)
                if sink:
                    sink.fallback_sink = self.fallback_sink
                    self.sinks.append(sink)
            return True
        except dbus.exceptions.DBusException:
            return False

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
        module_id = int(subprocess.check_output(cmd))
        if module_id > 0:
            self.update_sinks()
            for sink in self.sinks:
                if int(sink.module.index) == module_id:
                    return sink

    def delete_null_sink(self, id):
        cmd = [
            'pactl',
            'unload-module',
            str(id),
        ]
        try:
            subprocess.check_output(cmd)
        except:
            logger.error('Could not remove entity {id}'.format(id=id))


class PulseModuleFactory(object):

    @classmethod
    def new(self, bus, module_path):
        try:
            obj = bus.get_object(object_path=module_path)
            return PulseModule(
                object_path=unicode(module_path),
                index=unicode(obj.Get('org.PulseAudio.Core1.Module', 'Index')),
                name=unicode(obj.Get('org.PulseAudio.Core1.Module', 'Name')),
            )
        except dbus.exceptions.DBusException:
            logger.error('Could not get "{object_path}" from dbus.'.format(
                object_path=module_path))
            return None


@functools.total_ordering
class PulseModule(object):

    __shared_state = {}

    def __init__(self, object_path, index, name):
        if object_path not in self.__shared_state:
            self.__shared_state[object_path] = {}
        self.__dict__ = self.__shared_state[object_path]

        self.object_path = object_path
        self.index = index
        self.name = name

    def __eq__(self, other):
        return self.object_path == other.object_path

    def __gt__(self, other):
        return self.object_path > other.object_path

    def __str__(self):
        return '<PulseModule path="{}" name="{}" index="{}">\n'.format(
            self.object_path,
            self.name,
            self.index,
        )


class PulseSinkFactory(object):

    @classmethod
    def new(self, bus, object_path):
        try:
            obj = bus.get_object(object_path=object_path)

            properties = obj.Get('org.PulseAudio.Core1.Device', 'PropertyList')
            description_bytes = properties.get('device.description', [])
            label = self._convert_bytes_to_unicode(description_bytes)
            module_path = unicode(
                obj.Get('org.PulseAudio.Core1.Device', 'OwnerModule'))

            return PulseSink(
                object_path=unicode(object_path),
                index=unicode(obj.Get('org.PulseAudio.Core1.Device', 'Index')),
                name=unicode(obj.Get('org.PulseAudio.Core1.Device', 'Name')),
                label=label,
                module=PulseModuleFactory.new(bus, module_path),
            )
        except dbus.exceptions.DBusException:
            logger.error('Could not get "{object_path}" from dbus.'.format(
                object_path=object_path))
            return None

    @classmethod
    def _convert_bytes_to_unicode(self, byte_array):
        name = bytes()
        for i, b in enumerate(byte_array):
            if not (i == len(byte_array) - 1 and int(b) == 0):
                name += struct.pack('<B', b)
        return name.decode(locale.getpreferredencoding())


@functools.total_ordering
class PulseSink(object):

    __shared_state = {}

    def __init__(self, object_path, index, name, label, module,
                 fallback_sink=None):
        if object_path not in self.__shared_state:
            self.__shared_state[object_path] = {}
        self.__dict__ = self.__shared_state[object_path]

        self.object_path = object_path
        self.index = index
        self.name = name
        self.label = label or name
        self.module = module
        self.fallback_sink = fallback_sink

        self.monitor = self.name + '.monitor'
        self.streams = []

    def set_as_default_sink(self):
        cmd = [
            'pactl',
            'set-default-sink',
            str(self.index),
        ]
        subprocess.check_output(cmd)

    def switch_streams_to_fallback_source(self):
        if self.fallback_sink is not None:
            for stream in self.streams:
                stream.switch_to_source(self.fallback_sink.index)

    def __eq__(self, other):
        return self.object_path == other.object_path

    def __gt__(self, other):
        return self.object_path > other.object_path

    def __str__(self):
        string = ('<PulseSink path="{}" label="{}" name="{}" index="{}" '
                  'module="{}">\n').format(
            self.object_path,
            self.label,
            self.name,
            self.index,
            self.module.index,
        )
        if len(self.streams) == 0:
            string = string + '        -- no streams --'
        else:
            for stream in self.streams:
                string = string + '        {}\n'.format(stream)
        return string


class PulseStreamFactory(object):

    @classmethod
    def new(self, bus, stream_path):
        try:
            obj = bus.get_object(object_path=stream_path)
            return PulseStream(
                object_path=unicode(stream_path),
                index=unicode(obj.Get('org.PulseAudio.Core1.Stream', 'Index')),
                device=unicode(obj.Get('org.PulseAudio.Core1.Stream', 'Device')),
            )
        except dbus.exceptions.DBusException:
            logger.error('Could not get "{object_path}" from dbus.'.format(
                object_path=stream_path))
            return None


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

    def switch_to_source(self, index):
        cmd = [
            'pactl',
            'move-sink-input',
            str(self.index),
            str(index),
        ]
        subprocess.check_output(cmd)

    def __eq__(self, other):
        return self.object_path == other.object_path

    def __gt__(self, other):
        return self.object_path > other.object_path

    def __str__(self):
        return '<PulseStream path="{}" device="{}" index="{}">'.format(
            self.object_path,
            self.device,
            self.index,
        )


class PulseBridge(object):
    def __init__(self, sink, device):
        self.sink = sink
        self.device = device

    def __cmp__(self, other):
        if isinstance(other, PulseBridge):
            return (self.device == other.device and
                    self.sink == other.sink)
        if isinstance(other, pulseaudio_dlna.plugins.renderer.BaseRenderer):
            return self.device == other

    def __str__(self):
        return "<Bridge>\n    {}\n    {}\n".format(self.sink, self.device)


class PulseWatcher(PulseAudio):
    def __init__(self, bridges_shared, message_queue, disable_switchback=False, persist_stream=False):
        PulseAudio.__init__(self)

        self.bridges = []
        self.bridges_shared = bridges_shared
        self.devices = []

        self.message_queue = message_queue
        self.blocked_devices = []
        self.signal_timers = {}
        
        self.persist_stream = persist_stream

        self.disable_switchback = disable_switchback

        signals = (
            ('NewPlaybackStream', 'org.PulseAudio.Core1.{}',
                self.on_new_playback_stream),
            ('PlaybackStreamRemoved', 'org.PulseAudio.Core1.{}',
                self.on_playback_stream_removed),
            ('FallbackSinkUpdated', 'org.PulseAudio.Core1.{}',
                self.on_fallback_sink_updated),
            ('DeviceUpdated', 'org.PulseAudio.Core1.Stream.{}',
                self.on_device_updated),
        )
        self._connect(signals)
        self.update()
        self.default_sink = self.fallback_sink

    def terminate(self, signal_number=None, frame=None):
        self.cleanup()
        sys.exit(0)

    def run(self):
        signal.signal(signal.SIGINT, self.terminate)
        signal.signal(signal.SIGTERM, self.terminate)
        setproctitle.setproctitle('pulse_watcher')
        mainloop = gobject.MainLoop()
        gobject.timeout_add(500, self._check_message_queue)
        try:
            mainloop.run()
        except KeyboardInterrupt:
            pass

    def _check_message_queue(self):
        try:
            message = self.message_queue.get_nowait()
        except:
            return True

        message_type = message.get('type', None)
        if message_type and hasattr(self, message_type):
            del message['type']
            getattr(self, message_type)(**message)
        return True

    def _block_device_handling(self, object_path):
        self.blocked_devices.append(object_path)
        gobject.timeout_add(1000, self._unblock_device_handling, object_path)

    def _unblock_device_handling(self, object_path):
        self.blocked_devices.remove(object_path)

    def set_devices(self, devices):
        self.devices = devices
        self.update_bridges()
        self.share_bridges()

    def share_bridges(self):
        del self.bridges_shared[:]
        for bridge in copy.deepcopy(self.bridges):
            self.bridges_shared.append(bridge)

    def update_bridges(self):
        for device in self.devices:
            if device not in self.bridges:
                sink = self.create_null_sink(
                    device.short_name, device.label)
                self.bridges.append(PulseBridge(sink, device))

    def update(self):
        PulseAudio.update(self)
        self.share_bridges()

    def cleanup(self):
        for bridge in self.bridges:
            if self.persist_stream and bridge.device.state == bridge.device.PLAYING:
                logger.info('Stop silent stream on device "{}" ...'.format(bridge.device.label))
                bridge.device.stop()
            logger.info('Remove "{}" sink ...'.format(bridge.sink.name))
            self.delete_null_sink(bridge.sink.module.index)

    def _was_stream_moved(self, moved_stream, ignore_sink):
        for sink in self.system_sinks:
            if sink == ignore_sink:
                continue
            for stream in sink.streams:
                if stream == moved_stream:
                    return True
        for bridge in self.bridges:
            if bridge.sink == ignore_sink:
                continue
            for stream in bridge.sink.streams:
                if stream == moved_stream:
                    return True
        return False

    def switch_back(self, bridge, reason):
        title = 'Device "{label}"'.format(label=bridge.device.label)
        message = ('{reason}. Your streams were switched '
                   'back to <b>{name}</b>'.format(
                       reason=reason,
                       name=(self.fallback_sink.label).encode(
                           locale.getpreferredencoding())))
        pulseaudio_dlna.notification.show(title, message)

        self._block_device_handling(bridge.sink.object_path)
        if bridge.sink == self.default_sink:
            self.fallback_sink.set_as_default_sink()
        bridge.sink.switch_streams_to_fallback_source()

    def on_bridge_disconnected(self, stopped_bridge):

        for sink in self.sinks:
            if sink == stopped_bridge.sink:
                stopped_bridge.sink = sink
                break
        for bridge in self.bridges:
            if bridge.device == stopped_bridge.device:
                stopped_bridge.device = bridge.device
                break

        stopped_bridge.device.state = \
            pulseaudio_dlna.plugins.renderer.BaseRenderer.IDLE

        if not self.disable_switchback:
            reason = 'The device disconnected'
            if len(stopped_bridge.sink.streams) > 1:
                self.switch_back(stopped_bridge, reason)
            elif len(stopped_bridge.sink.streams) == 1:
                stream = stopped_bridge.sink.streams[0]
                if not self._was_stream_moved(stream, stopped_bridge.sink):
                    self.switch_back(stopped_bridge, reason)
            elif len(stopped_bridge.sink.streams) == 0:
                pass

    def on_device_updated(self, sink_path):
        logger.info('on_device_updated "{path}"'.format(
            path=sink_path))
        self.update()
        self._delayed_handle_sink_update(sink_path)

    def on_fallback_sink_updated(self, sink_path):
        self.default_sink = PulseSinkFactory.new(self.bus, sink_path)
        self.update()

    def on_new_playback_stream(self, stream_path):
        logger.info('on_new_playback_stream "{path}"'.format(
            path=stream_path))
        self.update()
        for sink in self.sinks:
            for stream in sink.streams:
                if stream.object_path == stream_path:
                    self._delayed_handle_sink_update(sink.object_path)
                    return

    def on_playback_stream_removed(self, stream_path):
        logger.info('on_playback_stream_removed "{path}"'.format(
            path=stream_path))
        for sink in self.sinks:
            for stream in sink.streams:
                if stream.object_path == stream_path:
                    self.update()
                    self._delayed_handle_sink_update(sink.object_path)
                    return

    def _delayed_handle_sink_update(self, sink_path):
        if self.signal_timers.get(sink_path, None):
            gobject.source_remove(self.signal_timers[sink_path])
        self.signal_timers[sink_path] = gobject.timeout_add(
            1000, self._handle_sink_update, sink_path)

    def _handle_sink_update(self, sink_path):
        logger.info('_handle_sink_update {}'.format(sink_path))
        if sink_path in self.signal_timers:
            del self.signal_timers[sink_path]

        if sink_path in self.blocked_devices:
            logger.info('{sink_path} was blocked!'.format(sink_path=sink_path))
            return

        for bridge in self.bridges:
            logger.debug('\n{}'.format(str(bridge)))
            if bridge.device.state == bridge.device.PLAYING:
                if len(bridge.sink.streams) == 0:
                    if not self.persist_stream:
                        logger.info(
                            'Instructing the device "{}" to stop ...'.format(
                                bridge.device.label))
                        return_code = bridge.device.stop()
                        if return_code == 200:
                            logger.info('The device "{}" was stopped.'.format(
                                bridge.device.label))
                        else:
                            logger.error(
                                'The device "{}" failed to stop! ({})'.format(
                                    bridge.device.label,
                                    return_code))
                    else:
                        logger.info(
                            'Continuing silent stream on device "{}" ...'.format(
                                bridge.device.label))
                    continue
            if bridge.sink.object_path == sink_path:
                if bridge.device.state == bridge.device.IDLE or \
                   bridge.device.state == bridge.device.PAUSE:
                    logger.info(
                        'Instructing the device "{}" to play ...'.format(
                            bridge.device.label))
                    return_code = bridge.device.play()
                    if return_code == 200:
                        logger.info('The device "{}" is playing.'.format(
                            bridge.device.label))
                    else:
                        logger.error(
                            'The device "{}" failed to play! ({})'.format(
                                bridge.device.label,
                                return_code))
                        self.switch_back(
                            bridge,
                            'The device failed to start playing. ({})'.format(
                                return_code))
        return False

    def add_device(self, device):
        self.devices.append(device)
        sink = self.create_null_sink(
            device.short_name, device.label)
        self.bridges.append(PulseBridge(sink, device))
        self.update()
        logger.info('Added the device "{name} ({flavour})".'.format(
            name=device.name, flavour=device.flavour))

    def remove_device(self, device):
        self.devices.remove(device)
        bridge_index_to_remove = None
        for index, bridge in enumerate(self.bridges):
            if bridge.device == device:
                logger.info('Remove "{}" sink ...'.format(bridge.sink.name))
                bridge_index_to_remove = index
                self.delete_null_sink(bridge.sink.module.index)
                break
        if bridge_index_to_remove is not None:
            self.bridges.pop(bridge_index_to_remove)
            self.update()
            logger.info('Removed the device "{name}".'.format(
                name=device.name))
