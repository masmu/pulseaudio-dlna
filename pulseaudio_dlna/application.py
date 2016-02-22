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
import pulseaudio_dlna.covermodes
import pulseaudio_dlna.streamserver
import pulseaudio_dlna.pulseaudio
import pulseaudio_dlna.utils.network
import pulseaudio_dlna.rules
import pulseaudio_dlna.renderers
import pulseaudio_dlna.discover

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

        if options['--ssdp-ttl']:
            ssdp_ttl = int(options['--ssdp-ttl'])
            pulseaudio_dlna.discover.RendererDiscover.SSDP_TTL = ssdp_ttl
            pulseaudio_dlna.listener.SSDPListener.SSDP_TTL = ssdp_ttl

        if options['--ssdp-mx']:
            ssdp_mx = int(options['--ssdp-mx'])
            pulseaudio_dlna.discover.RendererDiscover.SSDP_MX = ssdp_mx

        if options['--ssdp-amount']:
            ssdp_amount = int(options['--ssdp-amount'])
            pulseaudio_dlna.discover.RendererDiscover.SSDP_AMOUNT = ssdp_amount

        msearch_port = options.get('--msearch-port', None)
        if msearch_port != 'random':
            pulseaudio_dlna.discover.RendererDiscover.MSEARCH_PORT = \
                int(msearch_port)

        if options['--create-device-config']:
            self.create_device_config()
            sys.exit(0)

        if options['--update-device-config']:
            self.create_device_config(update=True)
            sys.exit(0)

        device_config = None
        if not options['--encoder'] and not options['--bit-rate']:
            device_config = self.read_device_config()

        if options['--encoder-backend']:
            try:
                pulseaudio_dlna.codecs.set_backend(
                    options['--encoder-backend'])
            except pulseaudio_dlna.codecs.UnknownBackendException as e:
                logger.error(e)
                sys.exit(1)

        if options['--encoder']:
            logger.warning(
                'The option "--encoder" is deprecated. '
                'Please use "--codec" instead.')
        codecs = (options['--encoder'] or options['--codec'])
        if codecs:
            try:
                pulseaudio_dlna.codecs.set_codecs(codecs.split(','))
            except pulseaudio_dlna.codecs.UnknownCodecException as e:
                logger.error(e)
                sys.exit(1)

        bit_rate = options['--bit-rate']
        if bit_rate:
            try:
                pulseaudio_dlna.encoders.set_bit_rate(bit_rate)
            except (pulseaudio_dlna.encoders.InvalidBitrateException,
                    pulseaudio_dlna.encoders.UnsupportedBitrateException) as e:
                logger.error(e)
                sys.exit(1)

        cover_mode = options['--cover-mode']
        try:
            pulseaudio_dlna.covermodes.validate(cover_mode)
        except pulseaudio_dlna.covermodes.UnknownCoverModeException as e:
            logger.error(e)
            sys.exit(1)

        logger.info('Encoder settings:')
        for _type in pulseaudio_dlna.encoders.ENCODERS:
            _type.AVAILABLE = False
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
            cover_mode=cover_mode,
        )

        device_filter = None
        if options['--filter-device']:
            device_filter = options['--filter-device'].split(',')

        locations = None
        disable_ssdp_search = False
        if options['--renderer-urls']:
            locations = options['--renderer-urls'].split(',')
            disable_ssdp_search = True

        if options['--request-timeout']:
            request_timeout = float(options['--request-timeout'])
            if request_timeout > 0:
                pulseaudio_dlna.plugins.renderer.BaseRenderer.REQUEST_TIMEOUT = \
                    request_timeout

        holder = pulseaudio_dlna.renderers.RendererHolder(
            self.PLUGINS, stream_server.ip, stream_server.port, message_queue,
            device_filter, device_config)

        if locations:
            holder.process_locations(locations)

        try:
            ssdp_listener = pulseaudio_dlna.listener.ThreadedSSDPListener(
                holder,
                disable_ssdp_listener=disable_ssdp_listener,
                disable_ssdp_search=disable_ssdp_search
            )
        except socket.error:
            logger.error(
                'The SSDP listener could not bind to the port 1900/UDP. '
                'Probably the port is in use by another application. '
                'Terminate the application which is using the port or run '
                'this application with the "--disable-ssdp-listener" flag.')
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

    def create_device_config(self, update=False):
        holder = pulseaudio_dlna.renderers.RendererHolder(self.PLUGINS)
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

        if update:
            existing_config = self.read_device_config()
            if existing_config:
                new_config = obj_to_dict(holder.renderers)
                new_config.update(existing_config)
            else:
                logger.error(
                    'Your device config could not be found at any of the '
                    'locations "{}"'.format(
                        ','.join(self.DEVICE_CONFIG_PATHS)))
                sys.exit(1)
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
                    logger.debug('Device configuration:\n{}'.format(json_text))
                    json_text = json_text.replace('\n', '')
                    try:
                        device_config = json.loads(json_text)
                        logger.info(
                            'Loaded device config "{}"'.format(config_file))
                        return device_config
                    except ValueError:
                        logger.error(
                            'Unable to parse "{}"! '
                            'Check the file for syntax errors ...'.format(
                                config_file))
        return None
