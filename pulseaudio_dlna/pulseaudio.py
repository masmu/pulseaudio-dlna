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

from gi.repository import GObject

import sys
import dbus
import dbus.mainloop.glib
import os
import struct
import subprocess
import logging
import setproctitle
import functools
import signal
import re
import traceback
import concurrent.futures
import collections

import pulseaudio_dlna.plugins.renderer
import pulseaudio_dlna.notification
import pulseaudio_dlna.utils.encoding
import pulseaudio_dlna.covermodes

logger = logging.getLogger('pulseaudio_dlna.pulseaudio')

MODULE_DBUS_PROTOCOL = 'module-dbus-protocol'
MODULE_NULL_SINK = 'module-null-sink'


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
        except Exception:
            logger.info(
                'Could not get default sink. Perhaps there is no one set?')

        system_sink_paths = self.core.Get(
            'org.PulseAudio.Core1', 'Sinks',
            dbus_interface='org.freedesktop.DBus.Properties')
        for sink_path in system_sink_paths:
            sink = PulseSinkFactory.new(self.bus, sink_path)
            if sink:
                self.system_sinks.append(sink)

    def _get_bus_addresses(self):
        bus_addresses = []

        def _probing_successful(name, _object):
            logger.info(
                'Probing for {} successful ({}).'.format(name, _object))

        def _probing_failed(name):
            logger.info(
                'Probing for {} unsuccessful.'.format(name))

        transports = os.environ.get('PULSE_DBUS_SERVER', None)
        if transports:
            _probing_successful('$PULSE_DBUS_SERVER', transports)
            for transport in transports.split(';'):
                if transport not in bus_addresses:
                    bus_addresses.append(transport)
        else:
            _probing_failed('$PULSE_DBUS_SERVER')

        possible_locations = [
            '/run/pulse/dbus-socket',
        ]
        for location in possible_locations:
            path = location.format(uid=os.getuid())
            if os.access(path, os.R_OK | os.W_OK):
                transport = 'unix:path={}'.format(path)
                _probing_successful(path, transport)
                if transport not in bus_addresses:
                    bus_addresses.append(transport)
            else:
                _probing_failed(path)

        path = os.environ.get('XDG_RUNTIME_DIR', None)
        if path:
            path = os.path.join(path, 'pulse/dbus-socket')
            if os.access(path, os.R_OK | os.W_OK):
                transport = 'unix:path={}'.format(path)
                _probing_successful('$XDG_RUNTIME_DIR', transport)
                if transport not in bus_addresses:
                    bus_addresses.append(transport)
            else:
                _probing_failed('$XDG_RUNTIME_DIR')
        else:
            _probing_failed('$XDG_RUNTIME_DIR')

        address = self.dbus_server_lookup()
        if address:
            _probing_successful('org.PulseAudio.ServerLookup1', address)
            if address not in bus_addresses:
                bus_addresses.append(address)
        else:
            _probing_failed('org.PulseAudio.ServerLookup1')

        return bus_addresses

    def _get_bus(self):

        modules = self.get_modules()
        if MODULE_DBUS_PROTOCOL not in modules:
            module_id = self.load_module(MODULE_DBUS_PROTOCOL)
            if module_id:
                logger.info('Module "{}" (id={}) loaded.'.format(
                    MODULE_DBUS_PROTOCOL, module_id))
            else:
                logger.critical(
                    'Failed to load module "{}"!'.format(MODULE_DBUS_PROTOCOL))
        else:
            logger.info(
                'Module "{}" already loaded.'.format(MODULE_DBUS_PROTOCOL))

        bus_addresses = self._get_bus_addresses()
        logger.info(
            'Found the following pulseaudio server addresses: {}'.format(
                ','.join(bus_addresses)))
        for bus_address in bus_addresses:
            try:
                logger.info('Connecting to pulseaudio on "{}" ...'.format(
                    bus_address))
                return dbus.connection.Connection(bus_address)
            except dbus.exceptions.DBusException:
                logger.info(traceback.format_exc())

        logger.critical(
            'Could not connect to pulseaudio! Application terminates!')
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
                'Could not update sinks and streams. This normally indicates '
                'a problem with pulseaudio\'s dbus module. Try restarting '
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

    def dbus_server_lookup(self):
        try:
            lookup_object = dbus.SessionBus().get_object(
                'org.PulseAudio1', '/org/pulseaudio/server_lookup1')
            address = lookup_object.Get(
                'org.PulseAudio.ServerLookup1',
                'Address',
                dbus_interface='org.freedesktop.DBus.Properties')
            return str(address)
        except dbus.exceptions.DBusException:
            return None

    def get_modules(self):
        process = subprocess.Popen(
            ['pactl', 'list', 'modules', 'short'],
            stdout=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode == 0:
            matches = re.findall(r'(\d+)\s+([\w-]+)(.*?)\n', stdout.decode())
            return [match[1] for match in matches]
        return None

    def load_module(self, module_name, options=None):
        command = ['pactl', 'load-module', module_name]
        if options:
            for key, value in list(options.items()):
                command.append('{}={}'.format(key, value))
        process = subprocess.Popen(command, stdout=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode == 0:
            return int(stdout.strip())
        return None

    def unload_module(self, module_id):
        process = subprocess.Popen(
            ['pactl', 'unload-module', str(module_id)],
            stdout=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            logger.error('Could not remove entity {id}'.format(id=module_id))

    def create_null_sink(self, sink_name, sink_description):
        options = collections.OrderedDict([
            ('sink_name', '"{}"'.format(sink_name)),
            ('sink_properties', 'device.description="{}"'.format(
                sink_description.replace(' ', '\ ')),)
        ])
        module_id = self.load_module(MODULE_NULL_SINK, options)
        if module_id > 0:
            self.update_sinks()
            for sink in self.sinks:
                if int(sink.module.index) == module_id:
                    return sink

    def delete_null_sink(self, module_id):
        return self.unload_module(module_id)


class PulseBaseFactory(object):

    @classmethod
    def _convert_bytes_to_unicode(self, byte_array):
        name = bytes()
        for i, b in enumerate(byte_array):
            if not (i == len(byte_array) - 1 and int(b) == 0):
                name += struct.pack('<B', b)
        return pulseaudio_dlna.utils.encoding.decode_default(name)


class PulseClientFactory(PulseBaseFactory):

    @classmethod
    def new(self, bus, client_path):
        try:
            obj = bus.get_object(object_path=client_path)
            properties = obj.Get('org.PulseAudio.Core1.Client', 'PropertyList')
            name_bytes = properties.get('application.name', [])
            icon_bytes = properties.get('application.icon_name', [])
            binary_bytes = properties.get('application.process.binary', [])
            return PulseClient(
                object_path=str(client_path),
                index=str(obj.Get('org.PulseAudio.Core1.Client', 'Index')),
                name=self._convert_bytes_to_unicode(name_bytes),
                icon=self._convert_bytes_to_unicode(icon_bytes),
                binary=self._convert_bytes_to_unicode(binary_bytes),
            )
        except dbus.exceptions.DBusException:
            logger.error(
                'PulseClientFactory - Could not get "{object_path}" '
                'from dbus.'.format(object_path=client_path))
            return None


@functools.total_ordering
class PulseClient(object):

    __shared_state = {}

    def __init__(self, object_path, index, name, icon, binary):
        if object_path not in self.__shared_state:
            self.__shared_state[object_path] = {}
        self.__dict__ = self.__shared_state[object_path]

        self.object_path = object_path
        self.index = index
        self.name = name or 'unknown'
        self.icon = icon or 'unknown'
        self.binary = binary or 'unknown'

    def __eq__(self, other):
        return self.object_path == other.object_path

    def __gt__(self, other):
        return self.object_path > other.object_path

    def __str__(self):
        return '<PulseClient path="{}" index="{}" name="{}" icon="{}" ' \
               'binary="{}">\n'.format(
                   self.object_path,
                   self.index,
                   self.name,
                   self.icon,
                   self.binary
               )


class PulseModuleFactory(PulseBaseFactory):

    @classmethod
    def new(self, bus, module_path):
        try:
            obj = bus.get_object(object_path=module_path)
            return PulseModule(
                object_path=str(module_path),
                index=str(obj.Get('org.PulseAudio.Core1.Module', 'Index')),
                name=str(obj.Get('org.PulseAudio.Core1.Module', 'Name')),
            )
        except dbus.exceptions.DBusException:
            logger.error(
                'PulseModuleFactory - Could not get "{object_path}" '
                'from dbus.'.format(object_path=module_path))
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


class PulseSinkFactory(PulseBaseFactory):

    @classmethod
    def new(self, bus, object_path):
        try:
            obj = bus.get_object(object_path=object_path)

            properties = obj.Get('org.PulseAudio.Core1.Device', 'PropertyList')
            description_bytes = properties.get('device.description', [])
            module_path = str(
                obj.Get('org.PulseAudio.Core1.Device', 'OwnerModule'))

            return PulseSink(
                object_path=str(object_path),
                index=str(obj.Get('org.PulseAudio.Core1.Device', 'Index')),
                name=str(obj.Get('org.PulseAudio.Core1.Device', 'Name')),
                label=self._convert_bytes_to_unicode(description_bytes),
                module=PulseModuleFactory.new(bus, module_path),
            )
        except dbus.exceptions.DBusException:
            logger.error(
                'PulseSinkFactory - Could not get "{object_path}" '
                'from dbus.'.format(object_path=object_path))
            return None


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

    @property
    def stream_client_names(self):
        names = []
        for stream in self.streams:
            try:
                names.append(stream.client.name)
            except Exception:
                names.append('?')
        return names

    @property
    def primary_application_name(self):
        for stream in self.streams:
            if stream.client.icon != 'unknown' and stream.client.icon != '':
                return stream.client.icon
        return None

    def set_as_default_sink(self):
        process = subprocess.Popen(
            ['pactl', 'set-default-sink', str(self.index)],
            stdout=subprocess.PIPE)
        process.communicate()
        if process.returncode == 0:
            return True
        return None

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
            self.module.index if self.module else None,
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
            client_path = str(
                obj.Get('org.PulseAudio.Core1.Stream', 'Client'))
            return PulseStream(
                object_path=str(stream_path),
                index=str(obj.Get(
                    'org.PulseAudio.Core1.Stream', 'Index')),
                device=str(obj.Get(
                    'org.PulseAudio.Core1.Stream', 'Device')),
                client=PulseClientFactory.new(bus, client_path),
            )
        except dbus.exceptions.DBusException:
            logger.debug(
                'PulseStreamFactory - Could not get "{object_path}" '
                'from dbus.'.format(object_path=stream_path))
            return None


@functools.total_ordering
class PulseStream(object):

    __shared_state = {}

    def __init__(self, object_path, index, device, client):
        if object_path not in self.__shared_state:
            self.__shared_state[object_path] = {}
        self.__dict__ = self.__shared_state[object_path]

        self.object_path = object_path
        self.index = index
        self.device = device
        self.client = client

    def switch_to_source(self, index):
        process = subprocess.Popen(
            ['pactl', 'move-sink-input', str(self.index), str(index)],
            stdout=subprocess.PIPE)
        process.communicate()
        if process.returncode == 0:
            return True
        return None

    def __eq__(self, other):
        return self.object_path == other.object_path

    def __gt__(self, other):
        return self.object_path > other.object_path

    def __str__(self):
        return '<PulseStream path="{}" device="{}" index="{}" ' \
               'client="{}">'.format(
                   self.object_path,
                   self.device,
                   self.index,
                   self.client.index if self.client else None,
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
        return '<Bridge>\n    {}\n    {}\n'.format(self.sink, self.device)


class PulseWatcher(PulseAudio):

    ASYNC_EXECUTION = True

    def __init__(self, pulse_queue, stream_queue, disable_switchback=False,
                 disable_device_stop=False, disable_auto_reconnect=True,
                 cover_mode='application', proc_title=None):
        PulseAudio.__init__(self)

        self.bridges = []
        self.pulse_queue = pulse_queue
        self.stream_queue = stream_queue
        self.blocked_devices = []
        self.signal_timers = {}
        self.is_terminating = False
        self.cover_mode = pulseaudio_dlna.covermodes.MODES[cover_mode]()
        self.proc_title = proc_title

        self.disable_switchback = disable_switchback
        self.disable_device_stop = disable_device_stop
        self.disable_auto_reconnect = disable_auto_reconnect

    def shutdown(self, signal_number=None, frame=None):
        if not self.is_terminating:
            logger.info('PulseWatcher.shutdown()')
            self.is_terminating = True
            self.cleanup()
            sys.exit(0)

    def run(self):
        signal.signal(signal.SIGTERM, self.shutdown)
        if self.proc_title:
            setproctitle.setproctitle(self.proc_title)

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
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

        self.thread_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        mainloop = GObject.MainLoop()
        GObject.io_add_watch(
            self.pulse_queue._reader, GObject.IO_IN | GObject.IO_PRI,
            self._on_new_message)
        try:
            mainloop.run()
        except KeyboardInterrupt:
            self.shutdown()

    def _on_new_message(self, fd, condition):
        try:
            message = self.pulse_queue.get_nowait()
        except Exception:
            return True

        message_type = message.get('type', None)
        if message_type and hasattr(self, message_type):
            del message['type']
            getattr(self, message_type)(**message)
        return True

    def _block_device_handling(self, object_path):
        self.blocked_devices.append(object_path)
        GObject.timeout_add(1000, self._unblock_device_handling, object_path)

    def _unblock_device_handling(self, object_path):
        self.blocked_devices.remove(object_path)

    def share_bridges(self):
        self.stream_queue.put({
            'type': 'update_bridges',
            'bridges': self.bridges,
        })

    def cleanup(self):
        for bridge in self.bridges:
            logger.info('Remove "{}" sink ...'.format(bridge.sink.name))
            self.delete_null_sink(bridge.sink.module.index)
        self.bridges = []
        sys.exit(0)

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
        if self.fallback_sink:
            message = ('{reason} Your streams were switched '
                       'back to <b>{name}</b>'.format(
                           reason=reason,
                           name=self.fallback_sink.label))
            pulseaudio_dlna.notification.show(title, message)

            self._block_device_handling(bridge.sink.object_path)
            if bridge.sink == self.default_sink:
                self.fallback_sink.set_as_default_sink()
            bridge.sink.switch_streams_to_fallback_source()
        else:
            message = ('Your streams could not get switched back because you '
                       'did not set a default sink in pulseaudio.')
            pulseaudio_dlna.notification.show(title, message)

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
            pulseaudio_dlna.plugins.renderer.BaseRenderer.STATE_STOPPED

        reason = 'The device disconnected'
        if len(stopped_bridge.sink.streams) > 1:
            if not self.disable_auto_reconnect:
                self._handle_sink_update(stopped_bridge.sink.object_path)
            elif not self.disable_switchback:
                self.switch_back(stopped_bridge, reason)
        elif len(stopped_bridge.sink.streams) == 1:
            stream = stopped_bridge.sink.streams[0]
            if not self._was_stream_moved(stream, stopped_bridge.sink):
                if not self.disable_auto_reconnect:
                    self._handle_sink_update(stopped_bridge.sink.object_path)
                elif not self.disable_switchback:
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
            GObject.source_remove(self.signal_timers[sink_path])
        self.signal_timers[sink_path] = GObject.timeout_add(
            1000, self._handle_sink_update, sink_path)

    def _handle_sink_update(self, sink_path):
        if not self.ASYNC_EXECUTION:
            logger.info('_sync_handle_sink_update {}'.format(sink_path))
            result = self.__handle_sink_update(sink_path)
            logger.info(
                '_sync_handle_sink_update {} finished!'.format(sink_path))
        else:
            logger.info('_async_handle_sink_update {}'.format(sink_path))
            future = self.thread_pool.submit(
                self.__handle_sink_update, sink_path)
            result = future.result()
            logger.info(
                '_async_handle_sink_update {} finished!'.format(sink_path))
        return result

    def __handle_sink_update(self, sink_path):
        if sink_path in self.signal_timers:
            del self.signal_timers[sink_path]

        if sink_path in self.blocked_devices:
            logger.info('{sink_path} was blocked!'.format(sink_path=sink_path))
            return

        for bridge in self.bridges:
            logger.debug('\n{}'.format(bridge))
            if bridge.device.state == bridge.device.STATE_PLAYING:
                if len(bridge.sink.streams) == 0 and (
                        not self.disable_device_stop and
                        'DISABLE_DEVICE_STOP' not in bridge.device.rules):
                    logger.info(
                        'Instructing the device "{}" to stop ...'.format(
                            bridge.device.label))
                    return_code, message = bridge.device.stop()
                    if return_code == 200:
                        logger.info(
                            'The device "{}" was stopped.'.format(
                                bridge.device.label))
                    else:
                        if not message:
                            message = 'Unknown reason.'
                        logger.error(
                            'The device "{}" failed to stop! ({}) - {}'.format(
                                bridge.device.label,
                                return_code,
                                message))
                        self.switch_back(bridge, message)
                    continue
            if bridge.sink.object_path == sink_path:
                if bridge.device.state == bridge.device.STATE_STOPPED or \
                   bridge.device.state == bridge.device.STATE_PAUSED:
                    logger.info(
                        'Instructing the device "{}" to play ...'.format(
                            bridge.device.label))
                    artist, title, thumb = self.cover_mode.get(bridge)
                    return_code, message = bridge.device.play(
                        artist=artist, title=title, thumb=thumb)
                    if return_code == 200:
                        logger.info(
                            'The device "{}" is playing.'.format(
                                bridge.device.label))
                    else:
                        if not message:
                            message = 'Unknown reason.'
                        logger.error(
                            'The device "{}" failed to play! ({}) - {}'.format(
                                bridge.device.label,
                                return_code,
                                message))
                        self.switch_back(bridge, message)
        return False

    def add_device(self, device):
        sink = self.create_null_sink(
            device.short_name, device.label)
        self.bridges.append(PulseBridge(sink, device))
        self.update()
        self.share_bridges()
        logger.info('Added the device "{name} ({flavour})".'.format(
            name=device.name, flavour=device.flavour))

    def remove_device(self, device):
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
            self.share_bridges()
            logger.info('Removed the device "{name}".'.format(
                name=device.name))

    def update_device(self, device):
        for bridge in self.bridges:
            if bridge.device == device:
                if bridge.device.ip != device.ip or \
                   bridge.device.port != device.port:
                    bridge.device.ip = device.ip
                    bridge.device.port = device.port
                    logger.info(
                        'Updated device "{}" - New settings: {}:{}'.format(
                            device.label, device.ip, device.port))
                    self.update()
                    self.share_bridges()
                    break
