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
    pulse-dlna.py --host <host> [--port <port>] [--encoder <encoder>]
    pulse-dlna.py [-h | --help | --version]

Options:
       --host=<host>        set the server ip.
    -p --port=<port>        set the server port [default: 8080].
    -e --encoder=<encoder>  set the server port [default: lame].
                            encoders are:
                              - lame  MPEG Audio Layer III (MP3)
                              - ogg   Ogg Vorbis
                              - flac  Free Lossless Audio Codec (FLAC)
                              - wav   Waveform Audio File Format (WAV)
    -v --version            show the version.
    -h --help               show the help.
    --debug                 enable debugging.
'''

import gobject
import dbus
import dbus.mainloop.glib
import multiprocessing
import logging
import sys

import docopt
import upnp.discover
import upnp.server
import pulseaudio


def main():
    logging.basicConfig(level=logging.INFO)
    options = docopt.docopt(__doc__, version='0.2')

    if not options['--host']:
        print('You must specify host address!')
        sys.exit(1)
    else:
        host = str(options['--host'])
        port = int(options['--port'])

    dlna_discover = upnp.discover.UpnpMediaRendererDiscover(host)
    dlna_discover.search()

    dlna_server = upnp.server.ThreadedDlnaServer(
        host, port, encoder=options['--encoder'])

    server_url = dlna_server.get_server_url()
    upnp_devices = []
    for upnp_device in dlna_discover.renderers:
        upnp_device.set_server_url(server_url)
        upnp_devices.append(upnp_device)
        logging.info('found upnp_device "{}"'.format(upnp_device))

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
