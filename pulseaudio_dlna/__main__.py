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
    pulseaudio-dlna [--host <host>] [--port <port>] [--encoder <encoder>] [--bit-rate=<rate>] [--filter-device=<filter-device>] [--renderer-urls <urls>] [--debug]
    pulseaudio-dlna [-h | --help | --version]

Options:
       --host=<host>                       Set the server ip.
    -p --port=<port>                       Set the server port [default: 8080].
    -e --encoder=<encoder>                 Set the audio encoder.
                                           Possible encoders are:
                                             - mp3   MPEG Audio Layer III (MP3)
                                             - ogg   Ogg Vorbis
                                             - flac  Free Lossless Audio Codec (FLAC)
                                             - wav   Waveform Audio File Format (WAV)
                                             - opus  Opus Interactive Audio Codec (OPUS)
    -b --bit-rate=<rate>                   Set the audio encoder's bitrate.
    --filter-device=<filter-device>        Set a name filter for devices which should be added.
                                           Devices which get discovered, but won't match the
                                           filter text will be skipped.
    --renderer-urls=<urls>                 Set the renderer urls yourself. no discovery will commence.
    --debug                                enables detailed debug messages.
    -v --version                           Show the version.
    -h --help                              Show the help.
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
