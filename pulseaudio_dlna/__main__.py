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

'''
Usage:
    pulseaudio-dlna [--host <host>] [--port <port>][--encoder <encoders> | --codec <codec>] [--bit-rate=<rate>]
                    [--encoder-backend <encoder-backend>]
                    [--filter-device=<filter-device>]
                    [--renderer-urls <urls>]
                    [--request-timeout <timeout>]
                    [--chunk-size <chunk-size>]
                    [--msearch-port=<msearch-port>] [--ssdp-mx <ssdp-mx>] [--ssdp-ttl <ssdp-ttl>] [--ssdp-amount <ssdp-amount>]
                    [--cover-mode <mode>]
                    [--auto-reconnect]
                    [--debug]
                    [--fake-http10-content-length] [--fake-http-content-length]
                    [--disable-switchback] [--disable-ssdp-listener] [--disable-device-stop] [--disable-workarounds] [--disable-mimetype-check]
    pulseaudio-dlna [--host <host>] [--create-device-config] [--update-device-config]
                    [--msearch-port=<msearch-port>] [--ssdp-mx <ssdp-mx>] [--ssdp-ttl <ssdp-ttl>] [--ssdp-amount <ssdp-amount>]
    pulseaudio-dlna [-h | --help | --version]

Options:
    --create-device-config                 Discovers all devices in your network and write a config for them.
                                           That config can be editied manually to adjust various settings.
                                           You can set:
                                             - Device name
                                             - Codec order (The first one is used if the encoder binary is available on your system)
                                             - Various codec settings such as the mime type, specific rules or
                                               the bit rate (depends on the codec)
                                           A written config is loaded by default if the --encoder and --bit-rate options are not used.
    --update-device-config                 Same as --create-device-config but preserves your existing config from being overwritten
       --host=<host>                       Set the server ip.
    -p --port=<port>                       Set the server port [default: 8080].
    -e --encoder=<encoders>                Deprecated alias for --codec
    -c --codec=<codecs>                    Set the audio codec.
                                           Possible codecs are:
                                             - mp3   MPEG Audio Layer III (MP3)
                                             - ogg   Ogg Vorbis (OGG)
                                             - flac  Free Lossless Audio Codec (FLAC)
                                             - wav   Waveform Audio File Format (WAV)
                                             - opus  Opus Interactive Audio Codec (OPUS)
                                             - aac   Advanced Audio Coding (AAC)
                                             - l16   Linear PCM (L16)
    --encoder-backend=<encoder-backend>    Set the backend for all encoders.
                                           Possible backends are:
                                             - generic (default)
                                             - ffmpeg
                                             - avconv
    -b --bit-rate=<rate>                   Set the audio encoder's bitrate.
    --filter-device=<filter-device>        Set a name filter for devices which should be added.
                                           Devices which get discovered, but won't match the
                                           filter text will be skipped.
    --renderer-urls=<urls>                 Set the renderer urls yourself. no discovery will commence.
    --request-timeout=<timeout>            Set the timeout for requests in seconds [default: 15].
    --chunk-size=<chunk-size>              Set the stream's chunk size [default: 4096].
    --ssdp-ttl=<ssdp-ttl>                  Set the SSDP socket's TTL [default: 10].
    --ssdp-mx=<ssdp-mx>                    Set the MX value of the SSDP discovery message [default: 3].
    --ssdp-amount=<ssdp-amount>            Set the amount of SSDP discovery messages being sent [default: 5].
    --msearch-port=<msearch-port>          Set the source port of the MSEARCH socket [default: random].
    --cover-mode=<mode>                    Set the cover mode [default: default].
                                           Possible modes are:
                                             - disabled       No icon is shown
                                             - default        The application icon is shown
                                             - distribution   The icon of your distribution is shown
                                             - application    The audio application's icon is shown
    --debug                                enables detailed debug messages.
    --auto-reconnect                       If set, the application tries to reconnect devices in case the stream collapsed
    --fake-http-content-length             If set, the content-length of HTTP requests will be set to 100 GB.
    --disable-switchback                   If set, streams won't switched back to the default sink if a device disconnects.
    --disable-ssdp-listener                If set, the application won't bind to the port 1900 and therefore the automatic discovery of new devices won't work.
    --disable-device-stop                  If set, the application won't send any stop commands to renderers at all
    --disable-workarounds                  If set, the application won't apply any device workarounds
    --disable-mimetype-check               If set, the application won't check the device's mime type capabilities
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

import sys
import os
import docopt
import logging
import socket
import getpass


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

    if not acquire_lock():
        print('The application is shutting down, since there already seems to '
              'be a running instance.')
        return 1

    if os.geteuid() == 0:
        logger.info('Running as root. Starting daemon ...')
        import pulseaudio_dlna.daemon
        daemon = pulseaudio_dlna.daemon.Daemon()
        daemon.run()
    else:
        import pulseaudio_dlna.application
        app = pulseaudio_dlna.application.Application()
        app.run(options)
    return 0


def acquire_lock():
    acquire_lock._lock_socket = socket.socket(
        socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        name = '/com/masmu/pulseaudio_dlna/{}'.format(getpass.getuser())
        acquire_lock._lock_socket.bind('\0' + name)
        return True
    except socket.error:
        return False


if __name__ == "__main__":
    sys.exit(main())
