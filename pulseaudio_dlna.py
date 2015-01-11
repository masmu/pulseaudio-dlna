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
    pulseaudio_dlna.py [--host <host>] [--port <port>] [--encoder <encoder>] [--renderer-urls <urls>] [--debug]
    pulseaudio_dlna.py [-h | --help | --version]

Options:
       --host=<host>        set the server ip.
    -p --port=<port>        set the server port [default: 8080].
    -e --encoder=<encoder>  set the server port [default: lame].
                            encoders are:
                              - lame  MPEG Audio Layer III (MP3)
                              - ogg   Ogg Vorbis
                              - flac  Free Lossless Audio Codec (FLAC)
                              - wav   Waveform Audio File Format (WAV)
    --renderer-urls=<urls>  set the renderer urls yourself. no discovery will commence.
    --debug                 enables detailed debug messages.
    -v --version            show the version.
    -h --help               show the help.
'''

import gobject
import dbus
import dbus.mainloop.glib
import multiprocessing
import logging
import sys
import signal

import docopt
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

        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        self.startup()

    def shutdown(self, signal_number, frame):
        print('Application is shutting down.')
        if self.pulse != None:
            self.pulse.cleanup()
        if self.dlna_server != None:
            self.dlna_server.server_close()
        sys.exit(1)

    def startup(self):
        options = docopt.docopt(__doc__, version='0.2.1')

        if not options['--debug']:
            logging.basicConfig(level=logging.INFO)
        else:
            logging.basicConfig(level=logging.DEBUG)

        if not options['--host']:
            host = utils.network.default_ipv4()
            if host == None:
                print('I could not determiate your host address. '
                      'You must specify it yourself via the --host option!')
                sys.exit(1)
        else:
            host = str(options['--host'])

        port = int(options['--port'])

        print ('Using localhost: {host}:{port}'.format(
            host=host, port=port))

        if options['--renderer-urls']:
            for url in options['--renderer-urls'].split(','):
                renderer = upnp.renderer.UpnpMediaRendererFactory.from_url(
                    url, upnp.renderer.CoinedUpnpMediaRenderer)
                if renderer != None:
                    self.renderers.append(renderer)
        else:
            dlna_discover = upnp.discover.UpnpMediaRendererDiscover(host)
            dlna_discover.search()
            self.renderers = dlna_discover.renderers
            logging.info('Discovery complete. You can now use your upnp devices!')

        if len(self.renderers) == 0:
            print('There were no upnp devices found. Application terminates.')
            sys.exit(1)

        self.dlna_server = upnp.server.ThreadedDlnaServer(
            host, port, encoder=options['--encoder'])

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

        mainloop = gobject.MainLoop()
        mainloop.run()

def main():
    pulseaudio_dlna = PulseAudioDLNA()

if __name__ == '__main__':
    main()
