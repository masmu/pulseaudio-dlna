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

from __future__ import unicode_literals

import gobject
import dbus
import dbus.mainloop.glib
import multiprocessing
import logging
import sys

import docopt
import upnp.discover
import upnp.server
import upnp.renderer
import pulseaudio
import utils.network


def main():
    options = docopt.docopt(__doc__, version='0.2.2')

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

    renderers = []
    if options['--renderer-urls']:
        for url in options['--renderer-urls'].split(','):
            renderer = upnp.renderer.UpnpMediaRendererFactory.from_url(
                url, upnp.renderer.CoinedUpnpMediaRenderer)
            if renderer != None:
                renderers.append(renderer)
    else:
        dlna_discover = upnp.discover.UpnpMediaRendererDiscover(host)
        dlna_discover.search()
        renderers = dlna_discover.renderers
        logging.info('Discovery complete. You can now use your upnp devices!')

    if len(renderers) == 0:
        print('There were no upnp devices found. Application terminates.')
        sys.exit(1)

    dlna_server = upnp.server.ThreadedDlnaServer(
        host, port, encoder=options['--encoder'])

    server_url = dlna_server.get_server_url()
    upnp_devices = []
    for upnp_device in renderers:
        upnp_device.set_server_url(server_url)
        upnp_devices.append(upnp_device)

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    pulse = pulseaudio.PulseWatcher()
    pulse.set_upnp_devices(upnp_devices)

    dlna_server.set_bridges(pulse.bridges)
    process = multiprocessing.Process(target=dlna_server.serve_forever)
    process.start()

    try:
        mainloop = gobject.MainLoop()
        mainloop.run()
    except KeyboardInterrupt:
        print('interrupted')
    finally:
        pulse.cleanup()
        dlna_server.server_close()

if __name__ == '__main__':
    main()
