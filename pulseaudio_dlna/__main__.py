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

'''
Usage:
    pulseaudio-dlna [--host <host>] [--port <port>] [--encoder <encoder>] [--filter-device=<filter-device>] [--renderer-urls <urls>] [--debug]
    pulseaudio-dlna [-h | --help | --version]

Options:
       --host=<host>                       Set the server ip.
    -p --port=<port>                       Set the server port [default: 8080].
    -e --encoder=<encoder>                 Set the server port [default: lame].
                                           Possible encoders are:
                                             - lame  MPEG Audio Layer III (MP3)
                                             - ogg   Ogg Vorbis
                                             - flac  Free Lossless Audio Codec (FLAC)
                                             - wav   Waveform Audio File Format (WAV)
                                             - opus  Opus Interactive Audio Codec (OPUS)
    --filter-device=<filter-device>        Set a name filter for devices which should be added.
                                           Devices which get discovered, but won't match the
                                           filter text will be skipped.
    --renderer-urls=<urls>                 Set the renderer urls yourself. no discovery will commence.
    --debug                                enables detailed debug messages.
    -v --version                           Show the version.
    -h --help                              Show the help.
'''

from __future__ import unicode_literals

import gobject
import dbus
import dbus.mainloop.glib
import multiprocessing
import setproctitle
import logging
import sys
import signal
import socket

import docopt
import pulseaudio_dlna
import upnp.discover
import upnp.server
import upnp.renderer
import pulseaudio
import utils.network


class PulseAudioDLNA(object):
    def __init__(self):
        self.dlna_server = None
        self.pulse = None
        self.renderers = []

    def shutdown(self, signal_number=None, frame=None):
        print('Application is shutting down.')
        if self.pulse is not None:
            self.pulse.cleanup()
        if self.dlna_server is not None:
            self.dlna_server.server_close()
        sys.exit(1)

    def startup(self):
        options = docopt.docopt(__doc__, version=pulseaudio_dlna.__version__)

        if not options['--debug']:
            logging.basicConfig(level=logging.INFO)
        else:
            logging.basicConfig(level=logging.DEBUG)

        if not options['--host']:
            host = utils.network.default_ipv4()
            if host is None:
                print('I could not determiate your host address. '
                      'You must specify it yourself via the --host option!')
                sys.exit(1)
        else:
            host = str(options['--host'])

        port = int(options['--port'])

        print('Using localhost: {host}:{port}'.format(
            host=host, port=port))

        if options['--renderer-urls']:
            for url in options['--renderer-urls'].split(','):
                renderer = upnp.renderer.UpnpMediaRendererFactory.from_url(
                    url, upnp.renderer.CoinedUpnpMediaRenderer)
                if renderer is not None:
                    self.renderers.append(renderer)
        else:
            device_filter = None
            if options['--filter-device']:
                device_filter = options['--filter-device'].split(',')
            dlna_discover = upnp.discover.UpnpMediaRendererDiscover(
                device_filter=device_filter)
            dlna_discover.search()
            self.renderers = dlna_discover.renderers
            logging.info('Discovery complete.')

        if len(self.renderers) == 0:
            print('There were no upnp devices found. Application terminates.')
            sys.exit(1)
        else:
            logging.info('Found devices:')
            for upnp_device in self.renderers:
                print(upnp_device)
            logging.info('You can now use your upnp devices!')

        try:
            self.dlna_server = upnp.server.ThreadedDlnaServer(
                host, port, encoder=options['--encoder'])
        except socket.error:
            print('The dlna server could not bind to your specified port '
                  '({port}). Perhaps this is already in use? Application '
                  'terminates.'.format(port=port))
            sys.exit(1)

        server_url = self.dlna_server.get_server_url()
        upnp_devices = []
        for upnp_device in self.renderers:
            upnp_device.set_server_url(server_url)
            upnp_devices.append(upnp_device)

        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.pulse = pulseaudio.PulseWatcher()
        self.pulse.set_upnp_devices(upnp_devices)

        self.dlna_server.set_bridges(self.pulse.bridges)
        process = multiprocessing.Process(target=self.dlna_server.serve_forever)
        process.start()

        setproctitle.setproctitle('pulseaudio-dlna')
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
        try:
            mainloop = gobject.MainLoop()
            mainloop.run()
        except KeyboardInterrupt:
            process.terminate()
            pass


def main(argv=sys.argv[1:]):
    pulseaudio_dlna = PulseAudioDLNA()
    pulseaudio_dlna.startup()


if __name__ == "__main__":
    sys.exit(main())
