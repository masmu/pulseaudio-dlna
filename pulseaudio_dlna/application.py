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

import multiprocessing
import signal
import setproctitle
import logging
import sys
import json
import os
import time

import pulseaudio_dlna
import pulseaudio_dlna.holder
import pulseaudio_dlna.plugins.dlna
import pulseaudio_dlna.plugins.dlna.ssdp
import pulseaudio_dlna.plugins.dlna.ssdp.listener
import pulseaudio_dlna.plugins.dlna.ssdp.discover
import pulseaudio_dlna.plugins.chromecast
import pulseaudio_dlna.encoders
import pulseaudio_dlna.covermodes
import pulseaudio_dlna.streamserver
import pulseaudio_dlna.pulseaudio
import pulseaudio_dlna.utils.network
import pulseaudio_dlna.rules
import pulseaudio_dlna.workarounds

logger = logging.getLogger('pulseaudio_dlna.application')


class Application(object):

    DEVICE_CONFIG_PATHS = [
        os.path.expanduser('~/.local/share/pulseaudio-dlna'),
        '/etc/pulseaudio-dlna',
    ]
    DEVICE_CONFIG = 'devices.json'
    PLUGINS = [
        pulseaudio_dlna.plugins.dlna.DLNAPlugin(),
        pulseaudio_dlna.plugins.chromecast.ChromecastPlugin(),
    ]
    SHUTDOWN_TIMEOUT = 5

    def __init__(self):
        self.processes = []
        self.is_terminating = False

    def shutdown(self, signal_number=None, frame=None):
        if not self.is_terminating:
            print('Application is shutting down ...')
            self.is_terminating = True

            for process in self.processes:
                # We send SIGINT to all subprocesses to trigger
                # KeyboardInterrupt and exit the mainloop
                # in those which use GObject.MainLoop().
                # This unblocks the main thread and ensures that the process
                # is receiving signals again.
                os.kill(process.pid, signal.SIGINT)
                # SIGTERM is the acutal one which is terminating the process
                os.kill(process.pid, signal.SIGTERM)

            start_time = time.time()
            while True:
                if time.time() - start_time >= self.SHUTDOWN_TIMEOUT:
                    print('Terminating remaining subprocesses ...')
                    for process in self.processes:
                        if process is not None and process.is_alive():
                            os.kill(process.pid, signal.SIGKILL)
                    sys.exit(1)
                time.sleep(0.1)
                all_dead = True
                for process in self.processes:
                    if process.is_alive():
                        all_dead = False
                        break
                if all_dead:
                    break
            sys.exit(0)

    def run_process(self, target, *args, **kwargs):
        process = multiprocessing.Process(
            target=target, args=args, kwargs=kwargs)
        self.processes.append(process)
        process.start()

    def run(self, options):

        logger.info('Using version: {}'.format(pulseaudio_dlna.__version__))

        if not options['--host']:
            host = None
        else:
            host = str(options['--host'])

        port = int(options['--port'])
        pulseaudio_dlna.streamserver.StreamServer.HOST = host
        pulseaudio_dlna.streamserver.StreamServer.PORT = port

        logger.info('Binding to {host}:{port}'.format(
            host=host or '*', port=port))

        if options['--disable-workarounds']:
            pulseaudio_dlna.workarounds.BaseWorkaround.ENABLED = False

        if options['--disable-ssdp-listener']:
            pulseaudio_dlna.plugins.dlna.ssdp.listener.\
                SSDPListener.DISABLE_SSDP_LISTENER = True

        if options['--disable-mimetype-check']:
            pulseaudio_dlna.plugins.renderer.DISABLE_MIMETYPE_CHECK = True

        if options['--chunk-size']:
            chunk_size = int(options['--chunk-size'])
            if chunk_size > 0:
                pulseaudio_dlna.streamserver.ProcessThread.CHUNK_SIZE = \
                    chunk_size

        if options['--ssdp-ttl']:
            ssdp_ttl = int(options['--ssdp-ttl'])
            pulseaudio_dlna.plugins.dlna.ssdp.discover.\
                SSDPDiscover.SSDP_TTL = ssdp_ttl
            pulseaudio_dlna.plugins.dlna.ssdp.listener.\
                SSDPListener.SSDP_TTL = ssdp_ttl

        if options['--ssdp-mx']:
            ssdp_mx = int(options['--ssdp-mx'])
            pulseaudio_dlna.plugins.dlna.ssdp.discover.\
                SSDPDiscover.SSDP_MX = ssdp_mx

        if options['--ssdp-amount']:
            ssdp_amount = int(options['--ssdp-amount'])
            pulseaudio_dlna.plugins.dlna.ssdp.discover.\
                SSDPDiscover.SSDP_AMOUNT = ssdp_amount

        msearch_port = options.get('--msearch-port', None)
        if msearch_port != 'random':
            pulseaudio_dlna.plugins.dlna.ssdp.discover.\
                SSDPDiscover.MSEARCH_PORT = int(msearch_port)

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
        for identifier, _type in pulseaudio_dlna.codecs.CODECS.items():
            codec = _type()
            logger.info('  {}'.format(codec))

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

        disable_device_stop = False
        if options['--disable-device-stop']:
            disable_device_stop = True

        disable_auto_reconnect = True
        if options['--auto-reconnect']:
            disable_auto_reconnect = False

        pulse_queue = multiprocessing.Queue()
        stream_queue = multiprocessing.Queue()

        stream_server = pulseaudio_dlna.streamserver.ThreadedStreamServer(
            host, port, pulse_queue, stream_queue,
            fake_http_content_length=fake_http_content_length,
            proc_title='stream_server',
        )

        pulse = pulseaudio_dlna.pulseaudio.PulseWatcher(
            pulse_queue, stream_queue,
            disable_switchback=disable_switchback,
            disable_device_stop=disable_device_stop,
            disable_auto_reconnect=disable_auto_reconnect,
            cover_mode=cover_mode,
            proc_title='pulse_watcher',
        )

        device_filter = None
        if options['--filter-device']:
            device_filter = options['--filter-device'].split(',')

        locations = None
        if options['--renderer-urls']:
            locations = options['--renderer-urls'].split(',')

        if options['--request-timeout']:
            request_timeout = float(options['--request-timeout'])
            if request_timeout > 0:
                pulseaudio_dlna.plugins.renderer.BaseRenderer.REQUEST_TIMEOUT = \
                    request_timeout

        holder = pulseaudio_dlna.holder.Holder(
            plugins=self.PLUGINS,
            pulse_queue=pulse_queue,
            device_filter=device_filter,
            device_config=device_config,
            proc_title='holder',
        )

        self.run_process(stream_server.run)
        self.run_process(pulse.run)
        if locations:
            self.run_process(holder.lookup, locations)
        else:
            self.run_process(holder.search, host=host)

        setproctitle.setproctitle('pulseaudio-dlna')
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        signal.signal(signal.SIGHUP, self.shutdown)
        signal.pause()

    def create_device_config(self, update=False):
        logger.info('Starting discovery ...')
        holder = pulseaudio_dlna.holder.Holder(plugins=self.PLUGINS)
        holder.search(ttl=5)
        logger.info('Discovery complete.')

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
                new_config = obj_to_dict(holder.devices)
                new_config.update(existing_config)
            else:
                logger.error(
                    'Your device config could not be found at any of the '
                    'locations "{}"'.format(
                        ','.join(self.DEVICE_CONFIG_PATHS)))
                sys.exit(1)
        else:
            new_config = obj_to_dict(holder.devices)
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
                    h.write(json_text)
                    logger.info('Found the following devices:')
                    for device in list(holder.devices.values()):
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
                    json_text = h.read()
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
