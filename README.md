# About #

This is _pulseaudio-dlna_. A small DLNA server which brings DLNA / UPNP
support to PulseAudio.

It can stream your current PulseAudio playback to different UPNP devices
(UPNP Media Renderers) in your network.
It's main goals are: easy to use, no configuration hassle, no
big dependencies.

![Image of pulseaudio-dlna](https://github.com/masmu/pulseaudio-dlna/blob/master/samples/images/pavucontrol-sample.png)


## License ##

    pulseaudio-dlna is licensed under GPLv3.

    pulseaudio-dlna is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    pulseaudio-dlna is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with pulseaudio-dlna.  If not, see <http://www.gnu.org/licenses/>.

## Installation ##

There is no special installation required. Just clone this git repository,
make sure you have all the dependencies installed and the PulseAudio DBus module
is loaded.

### Requirements ###
- python-dbus
- python-beautifulsoup
- python-docopt
- vorbis-tools
- sox
- lame
- flac

You can install all the dependencies in Ubuntu via:

    sudo apt-get install python-dbus python-beautifulsoup python-docopt vorbis-tools sox lame flac

### PulseAudio DBus module ###

You can do that via:

    pacmd load-module module-dbus-protocol

Or to make changes persistant edit the file `/etc/pulse/default.pa` with your
favorite editor and append the following line: 

    load-module module-dbus-protocol

### Starting ###

After that, you can start _pulseaudio-dlna_ via:

    ./pulseaudio-dlna.py --host <your-ip>

It should start searching for UPNP devices in your LAN and add new PulseAudio
sinks.
After that you can switch your playback streams via `pavucontrol` to be played
to a UPNP device.

You can install `pavucontrol` in Ubuntu via the following command:

    sudo apt-get install pavucontrol

Note that _pulseaudio-dlna_ has to run all the time while you are listening to
your music. If you stop _pulseaudio-dlna_ it will cleanly remove the created
UPNP devices from PulseAudio and your UPNP devices will stop playing.

Also note that _pulseaudio-dlna_ won't search for additional UPNP devices after
startup. It just does this once and (for me) there is no need in continuously
doing that. So if you added a new UPNP device to your network, restart
_pulseaudio-dlna_.

### CLI ###

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

Samples:
- `pulse-dlna.py --host 192.168.1.2 --encoder ogg` will start _pulse-dlna.py_
on port _8080_ and stream your PulseAudio streams encoded with _Ogg Vorbis_.
- `pulse-dlna.py --host 192.168.1.2 --port 10291 --encoder lame` will start 
_pulse-dlna.py_ on port _10291_ and stream your PulseAudio streams encoded
with _Ogg Vorbis_.

## Tested devices ##

_pulseaudio-dlna_ was successfully tested on the follwing devices / applications:

- D-Link DCH-M225/E
- Cocy UNPNP media render (https://github.com/mnlipp/CoCy)
- BubbleUPnP (Android App)

## Supported encoders ##

_pulseaudio-dlna_ supports the follwing encoders:

- __lame__  MPEG Audio Layer III (MP3)
- __ogg__   Ogg Vorbis
- __flac__  Free Lossless Audio Codec (FLAC)
- __wav__   Waveform Audio File Format (WAV)
