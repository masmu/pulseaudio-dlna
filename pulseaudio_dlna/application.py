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

import dbus
import dbus.mainloop.glib
import multiprocessing
import signal
import setproctitle
import logging
import sys
import socket

import pulseaudio_dlna
import pulseaudio_dlna.common
import pulseaudio_dlna.listener
import pulseaudio_dlna.plugins.upnp
import pulseaudio_dlna.plugins.chromecast
import pulseaudio_dlna.encoders
import pulseaudio_dlna.streamserver
import pulseaudio_dlna.pulseaudio
import pulseaudio_dlna.utils.network

logger = logging.getLogger('pulseaudio_dlna.application')


class Application(object):
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

        plugins = [
            pulseaudio_dlna.plugins.upnp.DLNAPlugin(),
            pulseaudio_dlna.plugins.chromecast.ChromecastPlugin(),
        ]

        if options['--encoder']:
            for identifier in options['--encoder'].split(','):
                found = False
                for codec in pulseaudio_dlna.common.supported_codecs:
                    if codec.identifier == identifier:
                        codec.enabled = True
                        found = True
                        continue
                if not found:
                    logger.error('You specified an unknown codec! '
                                 'Application terminates.')
                    sys.exit(1)
        else:
            for codec in pulseaudio_dlna.common.supported_codecs:
                codec.enabled = True

        if options['--bit-rate']:
            for codec in pulseaudio_dlna.common.supported_codecs:
                if not codec.enabled:
                    continue
                encoder = codec.encoder
                try:
                    encoder.default_bit_rate = options['--bit-rate']
                except pulseaudio_dlna.encoders.UnsupportedBitrateException:
                    continue
                except pulseaudio_dlna.encoders.InvalidBitrateException:
                    if len(encoder.supported_bit_rates) > 0:
                        logger.error(
                            'You specified an invalid bit rate '
                            'for the {encoder}!'
                            ' Supported bit rates '
                            'are "{bit_rates}"! '
                            'Application terminates.'.format(
                                encoder=encoder.__class__.__name__,
                                bit_rates=','.join(
                                    str(e) for e in encoder.supported_bit_rates
                                )))
                    else:
                        logger.error('Your selected encoder does not support '
                                     'setting a specific bit rate! '
                                     'Application terminates.')
                    sys.exit(1)

        logger.info('Loaded encoders:')
        for encoder in pulseaudio_dlna.common.supported_encoders:
            encoder.validate()
            logger.info(encoder)

        logger.info('Loaded codecs:')
        for codec in pulseaudio_dlna.common.supported_codecs:
            logger.info(codec)
        sys.exit(0)
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

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        pulse = pulseaudio_dlna.pulseaudio.PulseWatcher(
            bridges, message_queue,
            disable_switchback=disable_switchback,
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
                stream_server_address, message_queue, plugins,
                device_filter, locations, disable_ssdp_listener)
        except socket.error:
            logger.error(
                'The SSDP listener could not bind to the port 1900/UDP. '
                'Perhaps this is already in use? Application terminates. '
                'You can disable this feature with the '
                '"--disable-ssdp-listener" flag.')
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
