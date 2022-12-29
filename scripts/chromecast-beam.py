#!/usr/bin/python
# -*- coding: utf-8 -*-

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
    chromecast-beam.py <chromecast-host> <media-file>
    chromecast-beam.py [--host <host>] [-p <port>]
                       [--mime-type <mime-type>] [--debug]
                       [--network-address-translation]
                       [--audio-language=<audio-language>]
                       [--audio-track=<audio-track>]
                       [--audio-track-id=<audio-track-id>]
                       [--transcode <transcode>]
                       [--transcode-video <transcode-video>]
                       [--transcode-audio <transcode-audio>]
                       [--start-time=<start-time>]
                       [--sub-titles]
                       [--debug]
                       <chromecast-host> <media-file>

Options:
    -h --host=<host>                                     Bind to stream server socket to that host.
    -p --port=<port>                                     Set the server port [default: 8080].
    -n --network-address-translation                     Enable network address translation mode.
                                                            When used the application will fetch your
                                                            external IP address and bind to all local
                                                            interfaces. You just have to setup a port
                                                            forwarding in your router.
       --audio-language=<audio-language>                 Select the audio language.
       --audio-track=<audio-track>                       Select the audio track.
       --audio-track-id=<audio-track-id>                 Select the audio track ID.
    -t --transcode=<transcode>                           Enable transcoding [default: none].
                                                         Available options:
                                                            audio         - Transcode audio data
                                                            video         - Transcode video data
                                                            both          - Transcode both
    --transcode-video=<transcode-video>                  Select the transcoded video options.
                                                         Available options:
                                                            c|codec       - Set the codec
                                                            b|bitrate     - Set the bitrate
                                                            s|scale       - Set the scale
    --transcode-audio=<transcode-audio>                  Select the transcoded audio options.
                                                         Available options:
                                                            c|codec       - Set the codec
                                                            b|bitrate     - Set the bitrate
                                                            ch|channels   - Set the channels
                                                            s|samplerate  - Set the samplerate
                                                            l|language    - Set the language
    --start-time=<start-time>                            Set the start time of the video in seconds.
    --mime-type=<mime-type>                              Set the media's mimetype instead of guessing it.
    --sub-titles                                         Enable sub titles.
    --debug                                              Enable debug mode.

Examples:
       - chromecast-beam.py 192.168.1.2 ~/test.mkv

       will stream the file ~/test.mkv unmodified to the chromecast with the IP
       192.168.1.2

       - chromecast-beam.py --transcode=both 192.168.1.2 ~/test.mkv

       will transcode audio and video using the default settings and
       stream that to the Chromecast with the IP 192.168.1.2

       - chromecast-beam.py --audio-track 0 192.168.1.2 ~/test.mkv

       will just select audio line 0 from file ~/test.mkv and stream that to
       the Chromecast with the IP 192.168.1.2

       - chromecast-beam.py --audio-track 1 --transcode=audio 192.168.1.2 ~/test.mkv

       will just select audio line 1 from file ~/test.mkv, transcode that audio
       line using the transcode default settings and stream that with the
       unmodified video data to the Chromecast with the IP 192.168.1.2

       - chromecast-beam.py --audio-track 1 --transcode=video 192.168.1.2 ~/test.mkv

       will just select the unmodified audio line 1 from file ~/test.mkv,
       transcode the video data using the video transcode default settings and
       stream that with the unmodified video data to the Chromecast with the
       IP 192.168.1.2

       - chromecast-beam.py --transcode-video=b=2000,c=hevc 192.168.1.2 ~/test.mkv

       will transcode the video data using the encoder hevc and a bitrate
       of 2000 from file ~/test.mkv, and stream that to the Chromecast with the
       IP 192.168.1.2

       - chromecast-beam.py --transcode-video=b=2000,c=x264 --transcode-audio=b=256,c=mpga 192.168.1.2 ~/test.mkv

       will transcode the video data using the encoder x264 and a bitrate
       of 2000, transcode the audio line using the encoder mpga using a
       bitrate of 256 from file ~/test.mkv, and streams that to the Chromecast
       with the IP 192.168.1.2

'''


import docopt
import logging
import os
import threading
import mimetypes
import sys
import subprocess
import signal
import requests
import json
import shutil
import traceback
import re
import errno
import http.server
import socketserver
import pychromecast

import pulseaudio_dlna.utils.network

logger = logging.getLogger('chromecast-beam')

RE_IPV4 = r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
PORT_MIN = 1
PORT_MAX = 65535


class StoppableThread(threading.Thread):

    MODE_IMMEDIATE = 'immediate'

    def __init__(self, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.stop_event = threading.Event()
        self.stop_mode = None

    def stop(self, immediate=False):
        if not self.is_stopped:
            if immediate:
                self.stop_mode = immediate
            self.stop_event.set()

    def wait(self):
        self.stop_event.wait()

    @property
    def is_stopped(self):
        return self.stop_event.isSet()


class ChromecastThread(StoppableThread):

    PORT = 8009

    def __init__(self, chromecast_host, media_url, mime_type=None,
                 *args, **kwargs):
        StoppableThread.__init__(self, *args, **kwargs)
        self.chromecast_host = chromecast_host
        self.media_url = media_url
        self.mime_type = mime_type or 'video/mp4'
        self.desired_volume = 1.0
        self.timeout = 5

    def run(self):
        chromecast = pychromecast.Chromecast(
            host=chromecast_host, port=self.PORT, timeout=self.timeout)

        chromecast.media_controller.play_media(
            self.media_url,
            content_type=self.mime_type,
            stream_type=pychromecast.controllers.media.STREAM_TYPE_LIVE,
            autoplay=True,
        )

        logger.info(
            'Chromecast status: Volume {volume} ({muted})'.format(
                muted='Muted'
                if chromecast.media_controller.status.volume_muted
                else 'Unmuted',
                volume=chromecast.media_controller.status.volume_level * 100))

        self.wait()
        if self.stop_mode != StoppableThread.MODE_IMMEDIATE:
            chromecast.quit_app()


class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):

    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, file_uri, bind_host, request_host, port, handler=None):
        self.file_uri = file_uri
        self.file_path, self.file_name = os.path.split(self.file_uri)
        self.bind_host = bind_host
        self.request_host = request_host
        self.port = port
        self.handler = handler or DefaultRequestHandler

        os.chdir(self.file_path)
        socketserver.TCPServer.__init__(
            self, (self.bind_host, self.port), self.handler)

    @property
    def file_url(self):
        server_url = 'http://{host}:{port}'.format(
            host=self.request_host, port=self.port)
        return os.path.join(server_url, self.file_name)

    def handle_error(self, *args, **kwargs):
        self.shutdown()


class EncoderSettings(object):

    ENCODER_BINARY = '/usr/bin/vlc'

    TRANSCODE_USED = False

    TRANSCODE_VIDEO_CODEC = None
    TRANSCODE_VIDEO_BITRATE = None
    TRANSCODE_VIDEO_SCALE = None

    TRANSCODE_AUDIO_CODEC = None
    TRANSCODE_AUDIO_BITRATE = None
    TRANSCODE_AUDIO_CHANNELS = None
    TRANSCODE_AUDIO_SAMPLERATE = None
    TRANSCODE_AUDIO_LANG = None

    AUDIO_LANGUAGE = None
    AUDIO_TRACK = None
    AUDIO_TRACK_ID = None

    TRANSCODE_VIDEO_DEFAULTS_SET = False
    TRANSCODE_VIDEO_CODEC_DEF = 'h264'
    TRANSCODE_VIDEO_BITRATE_DEF = 3000
    TRANSCODE_VIDEO_SCALE_DEF = 'Auto'
    TRANSCODE_VIDEO_MUX_DEF = 'mkv'

    TRANSCODE_AUDIO_DEFAULTS_SET = False
    TRANSCODE_AUDIO_CODEC_DEF = 'mp3'
    TRANSCODE_AUDIO_BITRATE_DEF = 192
    TRANSCODE_AUDIO_CHANNELS_DEF = 2
    TRANSCODE_AUDIO_SAMPLERATE_DEF = 44100
    TRANSCODE_AUDIO_LANG_DEF = None

    START_TIME = None
    SUB_TITLES = False

    @classmethod
    def _decode_settings(cls, settings):
        try:
            data = {}
            for setting in settings.split(','):
                k, v = setting.split('=')
                data[k] = v
            return data
        except Exception:
            return {}

    @classmethod
    def _apply_option(cls, attribute, value):
        if attribute is not None:
            logger.info('{}={}'.format(attribute, value))
            setattr(cls, attribute, value)

    @classmethod
    def _apply_options(cls, options, option_map):
        for option, value in cls._decode_settings(options).items():
            attribute = option_map.get(option, None)
            cls._apply_option(attribute, value)

    @classmethod
    def set_video_defaults(cls):
        if cls.TRANSCODE_VIDEO_DEFAULTS_SET:
            return
        cls.TRANSCODE_VIDEO_DEFAULTS_SET = True
        cls._apply_option(
            'TRANSCODE_VIDEO_CODEC', cls.TRANSCODE_VIDEO_CODEC_DEF)
        cls._apply_option(
            'TRANSCODE_VIDEO_BITRATE', cls.TRANSCODE_VIDEO_BITRATE_DEF)
        cls._apply_option(
            'TRANSCODE_VIDEO_SCALE', cls.TRANSCODE_VIDEO_SCALE_DEF)

    @classmethod
    def set_audio_defaults(cls):
        if cls.TRANSCODE_AUDIO_DEFAULTS_SET:
            return
        cls.TRANSCODE_AUDIO_DEFAULTS_SET = True
        cls._apply_option(
            'TRANSCODE_AUDIO_CODEC', cls.TRANSCODE_AUDIO_CODEC_DEF)
        cls._apply_option(
            'TRANSCODE_AUDIO_BITRATE', cls.TRANSCODE_AUDIO_BITRATE_DEF)
        cls._apply_option(
            'TRANSCODE_AUDIO_CHANNELS', cls.TRANSCODE_AUDIO_CHANNELS_DEF)
        cls._apply_option(
            'TRANSCODE_AUDIO_SAMPLERATE', cls.TRANSCODE_AUDIO_SAMPLERATE_DEF)

    @classmethod
    def set_options(cls, options):
        used = False
        if options.get('--start-time', None):
            used = True
            cls.TRANSCODE_USED = True
            cls.set_video_defaults()
            cls._apply_option('START_TIME', options['--start-time'])
        if options.get('--sub-titles', None):
            used = True
            cls._apply_option('SUB_TITLES', True)
        if options.get('--audio-track', None):
            used = True
            cls.TRANSCODE_USED = True
            cls.set_audio_defaults()
            cls._apply_option('AUDIO_TRACK', options['--audio-track'])
        if options.get('--audio-language', None):
            used = True
            cls.TRANSCODE_USED = True
            cls.set_audio_defaults()
            cls._apply_option('AUDIO_LANGUAGE', options['--audio-language'])
        if options.get('--audio-track-id', None):
            used = True
            cls.TRANSCODE_USED = True
            cls.set_audio_defaults()
            cls._apply_option('AUDIO_TRACK_ID', options['--audio-track-id'])
        if options.get('--transcode', None):
            if options['--transcode'] in ['both', 'audio', 'video']:
                used = True
                cls.TRANSCODE_USED = True
            if options['--transcode'] in ['both', 'video']:
                cls.set_video_defaults()
            if options['--transcode'] in ['both', 'audio']:
                cls.set_audio_defaults()
        if options.get('--transcode-video', None):
            used = True
            cls.TRANSCODE_USED = True
            option_map = {
                'c': 'TRANSCODE_VIDEO_CODEC',
                'codec': 'TRANSCODE_VIDEO_CODEC',
                'b': 'TRANSCODE_VIDEO_BITRATE',
                'br': 'TRANSCODE_VIDEO_BITRATE',
                'bitrate': 'TRANSCODE_VIDEO_BITRATE',
                's': 'TRANSCODE_VIDEO_SCALE',
                'scale': 'TRANSCODE_VIDEO_SCALE',
            }
            cls.set_video_defaults()
            cls._apply_options(options['--transcode-video'], option_map)
        if options.get('--transcode-audio', None):
            used = True
            cls.TRANSCODE_USED = True
            option_map = {
                'c': 'TRANSCODE_AUDIO_CODEC',
                'codec': 'TRANSCODE_AUDIO_CODEC',
                'b': 'TRANSCODE_AUDIO_BITRATE',
                'br': 'TRANSCODE_AUDIO_BITRATE',
                'bitrate': 'TRANSCODE_AUDIO_BITRATE',
                'ch': 'TRANSCODE_AUDIO_CHANNELS',
                'channles': 'TRANSCODE_AUDIO_CHANNELS',
                's': 'TRANSCODE_AUDIO_SAMPLERATE',
                'sr': 'TRANSCODE_AUDIO_SAMPLERATE',
                'samplerate': 'TRANSCODE_AUDIO_SAMPLERATE',
                'l': 'TRANSCODE_AUDIO_LANG',
                'lang': 'TRANSCODE_AUDIO_LANG',
                'language': 'TRANSCODE_AUDIO_LANG',
            }
            cls.set_audio_defaults()
            cls._apply_options(options['--transcode-audio'], option_map)
        return used


class VLCEncoderSettings(EncoderSettings):

    @classmethod
    def _transcode_cmd_str(cls):
        options = {}
        if cls.TRANSCODE_VIDEO_CODEC:
            options['vcodec'] = cls.TRANSCODE_VIDEO_CODEC
        if cls.TRANSCODE_VIDEO_BITRATE:
            options['vb'] = cls.TRANSCODE_VIDEO_BITRATE
        if cls.TRANSCODE_VIDEO_SCALE:
            options['scale'] = cls.TRANSCODE_VIDEO_SCALE
        if cls.TRANSCODE_AUDIO_CODEC:
            options['acodec'] = cls.TRANSCODE_AUDIO_CODEC
        if cls.TRANSCODE_AUDIO_BITRATE:
            options['ab'] = cls.TRANSCODE_AUDIO_BITRATE
        if cls.TRANSCODE_AUDIO_CHANNELS:
            options['channels'] = cls.TRANSCODE_AUDIO_CHANNELS
        if cls.TRANSCODE_AUDIO_SAMPLERATE:
            options['samplerate'] = cls.TRANSCODE_AUDIO_SAMPLERATE
        if cls.TRANSCODE_AUDIO_LANG:
            options['alang'] = cls.TRANSCODE_AUDIO_LANG
        if cls.SUB_TITLES:
            options['soverlay'] = None
        return ','.join([
            '{}={}'.format(k, v) if v else k for k, v in options.items()
        ])

    @classmethod
    def command(cls, file_path):
        command = [
            cls.ENCODER_BINARY,
            '--intf', 'dummy',
            file_path,
            ':play-and-exit',
            ':no-sout-all',
        ]
        if cls.AUDIO_LANGUAGE:
            command.append(':audio-language=' + cls.AUDIO_LANGUAGE)
        if cls.AUDIO_TRACK:
            command.append(':audio-track=' + cls.AUDIO_TRACK)
        if cls.AUDIO_TRACK_ID:
            command.append(':audio-track-id=' + cls.AUDIO_TRACK_ID)
        if cls.START_TIME:
            command.append(':start-time=' + cls.START_TIME)
        if cls.TRANSCODE_USED:
            return command + [
                ':sout=#transcode{' + cls._transcode_cmd_str() + '}'
                ':std{access=file,mux=' + cls.TRANSCODE_VIDEO_MUX_DEF + ',dst=-}',
            ]
        else:
            return command + [
                ':sout=#file{access=file,mux=' + cls.TRANSCODE_VIDEO_MUX_DEF + ',dst=-}'
            ]


class DefaultRequestHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self, *args, **kwargs):
        logger.info('Serving unmodified media file to {} ...'.format(
            self.client_address[0]))
        http.server.SimpleHTTPRequestHandler.do_GET(self, *args, **kwargs)

    def log_request(self, code='-', size='-'):
        logger.info('{} - {}'.format(self.requestline, code))


class TranscodeRequestHandler(http.server.SimpleHTTPRequestHandler):

    def do_GET(self):
        try:
            client_address = self.client_address[0]
            logger.info('Serving transcoded media file to {} ...'.format(
                client_address))

            self.send_head()
            path = self.translate_path(self.path)
            command = VLCEncoderSettings.command(path)
            logger.info('Launching {}'.format(command))

            with open(os.devnull, 'w') as dev_null:
                encoder_process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=sys.stdout.fileno())
                shutil.copyfileobj(encoder_process.stdout, self.wfile)
        except IOError as e:
            if e.errno == errno.EPIPE:
                logger.info(
                    'Connection from {} closed.'.format(client_address))
            else:
                traceback.print_exc()
        except Exception:
            traceback.print_exc()
        finally:
            pid = encoder_process.pid
            logger.info('Terminating process {}'.format(pid))
            try:
                os.kill(pid, signal.SIGKILL)
            except Exception:
                pass

    def log_request(self, code='-', size='-'):
        logger.info('{} - {}'.format(self.requestline, code))


def get_external_ip():
    response = requests.get('http://ifconfig.lancode.de')
    if response.status_code == 200:
        data = json.loads(response.content)
        return data.get('ip', None)
    return None


# Local pulseaudio-dlna installations running in a virutalenv should run this
#   script as module:
#     python3 -m scripts.chromecast-beam 192.168.1.10 ~/videos/test.mkv

if __name__ == "__main__":

    options = docopt.docopt(__doc__, version='0.1')

    level = logging.DEBUG
    if not options['--debug']:
        level = logging.INFO
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('urllib3').setLevel(logging.WARNING)

    logging.basicConfig(
        level=level,
        format='%(asctime)s %(name)-46s %(levelname)-8s %(message)s',
        datefmt='%m-%d %H:%M:%S')

    media_file = options.get('<media-file>', None)
    if not os.path.isfile(media_file):
        logger.critical('{} is not a file!'.format(media_file))
        sys.exit(1)

    mime_type = options.get('--mime-type', None)
    if mime_type is None:
        mime_type, encoding = mimetypes.guess_type(media_file)

    try:
        port = int(options.get('--port'))
        if port < PORT_MIN or port > PORT_MAX:
            raise ValueError()
    except ValueError:
        logger.critical('Port {} is not a valid port number!'.format(
            options.get('--port')))
        sys.exit(1)

    chromecast_host = options.get('<chromecast-host>')
    if not re.match(RE_IPV4, chromecast_host):
        logger.critical('{} is no valid IP address!'.format(chromecast_host))
        sys.exit(1)

    host = options.get('--host', None)
    if options.get('--network-address-translation', None):
        bind_host = ''
        request_host = host or get_external_ip()
    else:
        bind_host = host or pulseaudio_dlna.utils.network.get_host_by_ip(
            chromecast_host)
        request_host = host or bind_host
    if request_host is None:
        logger.critical('Could not determine host address!')
        sys.exit(1)
    else:
        logger.info('Using host {}:{} '.format(
            '*' if bind_host == '' else bind_host, port))

    handler = DefaultRequestHandler
    if VLCEncoderSettings.set_options(options):
        handler = TranscodeRequestHandler

    http_server = ThreadedHTTPServer(
        media_file, bind_host, request_host, port, handler)
    chromecast_thread = ChromecastThread(
        chromecast_host, http_server.file_url, mime_type=mime_type)
    chromecast_thread.start()

    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        chromecast_thread.stop()
    finally:
        chromecast_thread.stop(immediate=True)
        chromecast_thread.join()
