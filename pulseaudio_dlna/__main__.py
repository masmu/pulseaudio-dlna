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
    pulseaudio-dlna [--host <host>] [--port <port>] [--encoder <encoders>] [--bit-rate=<rate>] [--filter-device=<filter-device>] [--renderer-urls <urls>] [--debug] [--fake-http10-content-length] [--fake-http-content-length] [--disable-switchback] [--disable-ssdp-listener]
    pulseaudio-dlna [-h | --help | --version]

Options:
       --host=<host>                       Set the server ip.
    -p --port=<port>                       Set the server port [default: 8080].
    -e --encoder=<encoders>                Set the audio encoder.
                                           Possible encoders are:
                                             - mp3   MPEG Audio Layer III (MP3)
                                             - ogg   Ogg Vorbis (OGG)
                                             - flac  Free Lossless Audio Codec (FLAC)
                                             - wav   Waveform Audio File Format (WAV)
                                             - opus  Opus Interactive Audio Codec (OPUS)
                                             - aac   Advanced Audio Coding (AAC)
                                             - l16   Linear PCM (L16)
    -b --bit-rate=<rate>                   Set the audio encoder's bitrate.
    --filter-device=<filter-device>        Set a name filter for devices which should be added.
                                           Devices which get discovered, but won't match the
                                           filter text will be skipped.
    --renderer-urls=<urls>                 Set the renderer urls yourself. no discovery will commence.
    --debug                                enables detailed debug messages.
    --fake-http-content-length             If set, the content-length of HTTP requests will be set to 100 GB.
    --disable-switchback                   If set, streams won't switched back to the default sink if a device disconnects.
    --disable-ssdp-listener                If set, the application won't bind to the port 1900 and therefore the automatic discovery of new devices won't work.
    -v --version                           Show the version.
    -h --help                              Show the help.

Examples:
      - pulseaudio-dlna

      will start pulseaudio-dlna on port 8080 and stream your PulseAudio streams encoded with mp3.

      - pulseaudio-dlna --encoder ogg

      will start pulseaudio-dlna on port 8080 and stream your PulseAudio streams encoded with Ogg Vorbis.

      - pulseaudio-dlna --port 10291 --encoder flac

      will start pulseaudio-dlna on port 10291 and stream your PulseAudio streams encoded with FLAC.

      - pulseaudio-dlna --filter-device 'Nexus 5,TV'

      will just use devices named Nexus 5 or TV even when more devices got discovered.

      - pulseaudio-dlna --renderer-urls http://192.168.1.7:7676/smp_10_

      won't discover upnp devices by itself. Instead it will search for upnp renderers
      at the specified locations. You can specify multiple locations via urls
      separated by comma (,). Most users won't ever need this option, but since
      UDP multicast packages won't work (most times) over VPN connections this is
      very useful if you ever plan to stream to a UPNP device over VPN.

'''


from __future__ import unicode_literals

import sys
import os
import docopt
import logging


def main(argv=sys.argv[1:]):

    import pulseaudio_dlna
    options = docopt.docopt(__doc__, version=pulseaudio_dlna.__version__)

    level = logging.DEBUG
    if not options['--debug']:
        level = logging.INFO
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)

    logging.basicConfig(
        level=level,
        format='%(asctime)s %(name)-46s %(levelname)-8s %(message)s',
        datefmt='%m-%d %H:%M:%S')
    logger = logging.getLogger('pulseaudio_dlna.__main__')

    if os.geteuid() == 0:
        logger.info('Running as root. Starting daemon ...')
        import pulseaudio_dlna.daemon
        daemon = pulseaudio_dlna.daemon.Daemon()
        daemon.run()
    else:
        import pulseaudio_dlna.application
        app = pulseaudio_dlna.application.Application()
        app.run(options)

if __name__ == "__main__":
    sys.exit(main())
