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

import multiprocessing
import signal
import setproctitle
import logging
import sys
import socket
import json
import os

import pulseaudio_dlna
import pulseaudio_dlna.listener
import pulseaudio_dlna.plugins.upnp
import pulseaudio_dlna.plugins.chromecast
import pulseaudio_dlna.encoders
import pulseaudio_dlna.streamserver
import pulseaudio_dlna.pulseaudio
import pulseaudio_dlna.utils.network
import pulseaudio_dlna.rules

logger = logging.getLogger('pulseaudio_dlna.application')


class Application(object):

    ENCODING = 'utf-8'
    DEVICE_CONFIG_PATHS = [
        os.path.expanduser('~/.local/share/pulseaudio-dlna'),
        '/etc/pulseaudio-dlna',
    ]
    DEVICE_CONFIG = 'devices.json'
    PLUGINS = [
        pulseaudio_dlna.plugins.upnp.DLNAPlugin(),
        pulseaudio_dlna.plugins.chromecast.ChromecastPlugin(),
    ]

    def __init__(self):
        self.processes = []

    def shutdown(self, signal_number=None, frame=None):
        print('Application is shutting down.')
        for process in self.processes:
            if process is not None and process.is_alive():
                process.terminate()
        sys.exit(0)

    def run_process(self, target):
        process = multiprocessing.Process(target=target)
        self.processes.append(process)
        process.start()

    def run(self, options):

        logger.info('Using version: {}'.format(pulseaudio_dlna.__version__))

        if not options['--host']:
            host = pulseaudio_dlna.utils.network.default_ipv4()
            if host is None:
                logger.info(
                    'I could not determine your host address. '
                    'You must specify it yourself via the --host option!')
                sys.exit(1)
        else:
            host = str(options['--host'])

        port = int(options['--port'])

        logger.info('Using localhost: {host}:{port}'.format(
            host=host, port=port))

        if options['--create-device-config']:
            self.create_device_config()
            sys.exit(0)

        device_config = None
        if not options['--encoder'] and not options['--bit-rate']:
            device_config = self.read_device_config()

        if options['--encoder']:
            for identifier, _type in pulseaudio_dlna.codecs.CODECS.iteritems():
                _type.ENABLED = False
            for identifier in options['--encoder'].split(','):
                try:
                    pulseaudio_dlna.codecs.CODECS[identifier].ENABLED = True
                    continue
                except KeyError:
                    logger.error('You specified an unknown codec! '
                                 'Application terminates.')
                    sys.exit(1)

        if options['--bit-rate']:
            try:
                bit_rate = int(options['--bit-rate'])
            except ValueError:
                logger.error('Bit rates must be specified as integers!')
                sys.exit(0)
            for _type in pulseaudio_dlna.encoders.ENCODERS:
                if hasattr(_type, 'DEFAULT_BIT_RATE') and \
                   hasattr(_type, 'SUPPORTED_BIT_RATES'):
                    if bit_rate in _type.SUPPORTED_BIT_RATES:
                        _type.DEFAULT_BIT_RATE = bit_rate
                    else:
                        logger.error(
                            'You specified an invalid bit rate '
                            'for the {encoder}!'
                            ' Supported bit rates '
                            'are "{bit_rates}"! '
                            'Application terminates.'.format(
                                encoder=_type().__class__.__name__,
                                bit_rates=','.join(
                                    str(e) for e in _type.SUPPORTED_BIT_RATES
                                )))
                        sys.exit(0)

        logger.info('Encoder settings:')
        for _type in pulseaudio_dlna.encoders.ENCODERS:
            encoder = _type()
            encoder.validate()
            logger.info('  {}'.format(encoder))

        logger.info('Codec settings:')
        for identifier, _type in pulseaudio_dlna.codecs.CODECS.iteritems():
            codec = _type()
            logger.info('  {}'.format(codec))

        manager = multiprocessing.Manager()
        message_queue = multiprocessing.Queue()
        bridges = manager.list()

        fake_http_content_length = False
        if options['--fake-http-content-length']:
            fake_http_content_length = True
        if options['--fake-http10-content-length']:
            logger.warning(
                'The option "--fake-http10-content-length" is deprecated. '
                'Please use "--fake-http-content-length" instead.')
            fake_http_content_length = True

        disable_switchback = False
        if options['--disable-switchback']:
            disable_switchback = True

        disable_ssdp_listener = False
        if options['--disable-ssdp-listener']:
            disable_ssdp_listener = True

        disable_device_stop = False
        if options['--disable-device-stop']:
            disable_device_stop = True

        try:
            stream_server = pulseaudio_dlna.streamserver.ThreadedStreamServer(
                host, port, bridges, message_queue,
                fake_http_content_length=fake_http_content_length,
            )
        except socket.error:
            logger.error(
                'The streaming server could not bind to your specified port '
                '({port}). Perhaps this is already in use? Application '
                'terminates.'.format(port=port))
            sys.exit(1)

        pulse = pulseaudio_dlna.pulseaudio.PulseWatcher(
            bridges, message_queue,
            disable_switchback=disable_switchback,
            disable_device_stop=disable_device_stop,
        )

        device_filter = None
        if options['--filter-device']:
            device_filter = options['--filter-device'].split(',')

        locations = None
        if options['--renderer-urls']:
            locations = options['--renderer-urls'].split(',')

        try:
            stream_server_address = stream_server.ip, stream_server.port
            ssdp_listener = pulseaudio_dlna.listener.ThreadedSSDPListener(
                stream_server_address, message_queue, self.PLUGINS,
                device_filter, device_config, locations, disable_ssdp_listener)
        except socket.error:
            logger.error(
                'The SSDP listener could not bind to the port 1900/UDP. '
                'Probably the port is in use by another application. '
                'Terminate the application which is using the port or run this '
                'application with the "--disable-ssdp-listener" flag.')
            sys.exit(1)

        self.run_process(target=stream_server.run)
        self.run_process(target=pulse.run)
        self.run_process(target=ssdp_listener.run)

        setproctitle.setproctitle('pulseaudio-dlna')
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGHUP, self.shutdown)

        for process in self.processes:
            process.join()

    def create_device_config(self):
        holder = pulseaudio_dlna.renderers.RendererHolder(
            ('', 0), multiprocessing.Queue(), self.PLUGINS)
        discover = pulseaudio_dlna.discover.RendererDiscover(holder)
        discover.search()

        def device_filter(obj):
            if hasattr(obj, 'to_json'):
                return obj.to_json()
            else:
                return obj.__dict__

        def obj_to_dict(obj):
            json_text = json.dumps(obj, default=device_filter)
            return json.loads(json_text)

        existing_config = self.read_device_config()
        if existing_config:
            new_config = obj_to_dict(holder.renderers)
            new_config.update(existing_config)
        else:
            new_config = obj_to_dict(holder.renderers)
        json_text = json.dumps(new_config, indent=4)

        for config_path in reversed(self.DEVICE_CONFIG_PATHS):
            config_file = os.path.join(config_path, self.DEVICE_CONFIG)
            if not os.path.exists(config_path):
                try:
                    os.makedirs(config_path)
                except (OSError, IOError):
                    continue
            try:
                with open(config_file, 'w') as h:
                    h.write(json_text.encode(self.ENCODING))
                    logger.info('Found the following devices:')
                    for device in holder.renderers.values():
                        logger.info('{name} ({flavour})'.format(
                            name=device.name, flavour=device.flavour))
                        for codec in device.codecs:
                            logger.info('  - {}'.format(
                                codec.__class__.__name__))
                    logger.info(
                        'Your config was successfully written to "{}"'.format(
                            config_file))
                    return
            except (OSError, IOError):
                continue

        logger.error(
            'Your device config could not be written to any of the '
            'locations "{}"'.format(','.join(self.DEVICE_CONFIG_PATHS)))

    def read_device_config(self):
        for config_path in self.DEVICE_CONFIG_PATHS:
            config_file = os.path.join(config_path, self.DEVICE_CONFIG)
            if os.path.isfile(config_file) and \
               os.access(config_file, os.R_OK):
                with open(config_file, 'r') as h:
                    json_text = h.read().decode(self.ENCODING)
                    logger.debug(
                        'Device configuration:\n{}'.format(
                            json_text))
                    json_text = json_text.replace('\n', '')
                    try:
                        device_config = json.loads(json_text)
                        logger.info(
                            'Loaded device config "{}"'.format(
                                config_file))
                        return device_config
                    except ValueError:
                        logger.error(
                            'Unable to parse "{}"! '
                            'Check the file for syntax errors ...'.format(
                                config_file))
        return None
