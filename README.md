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

## Donation ##
![Image of pulseaudio-dlna](http://maemo.lancode.de/.webdir/donate.gif)
If I could help you or if you like my work, you can buy me a [coffee, a beer or pizza](https://www.paypal.com/cgi-bin/webscr?cmd=_xclick&business=totalexceed%40lancode%2ede&item_name=Donation&no_shipping=2&no_note=1&tax=0&currency_code=EUR&bn=PP%2dDonationsBF&charset=UTF%2d8).

## Changelog ##

 * __0.2.4__ - (_2015-01-25_)
    - Stream changes are now handled correctly (thanks to [Takkat-Nebuk](https://github.com/Takkat-Nebuk))

 * __0.2.3__ - (_2015-01-21_)
    - Fixed a timing bug where the pulseaudio module was not loaded fast enough (thanks to [Takkat-Nebuk](https://github.com/Takkat-Nebuk))

 * __0.2.2__ - (_2015-01-18_)
    - Fixed encoding issues
    - Try to load the DBus module if it is not loaded before (thanks to [Takkat-Nebuk](https://github.com/Takkat-Nebuk))

 * __0.2.1__ - (_2015-01-11_)
    - TTL changed to 10 and timeout to 5 for UDP broadcasting
    - Added the ```--renderer-urls``` option to manually add UPNP devices via their control url
    - Added the ```--debug``` flag
    - The host ip address is now discovered automatically, no need to specifiy ```--host``` anymore

## Installation ##

There is no special installation required. Just clone this git repository,
make sure you have all the dependencies installed and the PulseAudio DBus module
is loaded.

### Requirements ###
- python-dbus
- python-beautifulsoup
- python-docopt
- python-requests
- vorbis-tools
- sox
- lame
- flac

You can install all the dependencies in Ubuntu via:

    sudo apt-get install python-dbus python-beautifulsoup python-docopt python-requests vorbis-tools sox lame flac

### PulseAudio DBus module ###

Since version _0.2.2_ the DBus module should be loaded automatically, if it was
not loaded before.
It that does not work, you can load the DBus module in Ubuntu via the following
command. Note that you 
have to do this every time you restart PulseAudio (or your computer).

    pacmd load-module module-dbus-protocol

Or to make changes persistant edit the file `/etc/pulse/default.pa` with your
favorite editor and append the following line: 

    load-module module-dbus-protocol

### Starting ###

After that, you can start _pulseaudio-dlna_ via:

    ./pulseaudio_dlna.py

_pulseaudio-dlna_ should detect the ip address your computer is reachable within
your local area network. If the detected ip address is not correct or there
were no ips found, you still can specifiy them yourself via: ```./pulseaudio_dlna.py --host <your-ip>```

Right after startup it should start searching for UPNP devices in your LAN and
add new PulseAudio sinks.
After 5 seconds the progress is complete and you can select your UPNP renderers
from the default audio control.

In case you just want to stream single audio streams to your UPNP devices you
can do this via `pavucontrol`.

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
        pulseaudio_dlna.py --host <host> [--port <port>] [--encoder <encoder>] [--renderer-urls <urls>]
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
        -v --version            show the version.
        -h --help               show the help.

Samples:
- `pulseaudio_dlna.py --host 192.168.1.2 --encoder ogg` will start 
_pulseaudio-dlna_ on port _8080_ and stream your PulseAudio streams encoded
with _Ogg Vorbis_.
- `pulseaudio_dlna.py --host 192.168.1.2 --port 10291 --encoder lame` will start 
_pulseaudio-dlna_ on port _10291_ and stream your PulseAudio streams encoded
with _mp3_.
- `pulseaudio_dlna.py --host 192.168.1.2 --renderer-urls http://192.168.1.7:7676/smp_10_`
won't discover upnp devices by itself. Instead it will search for upnp renderers
at the specified locations. You can specify multiple locations via urls
seperated by comma (_,_). Most users won't ever need this option, but since
UDP multicast packages won't work (most times) over VPN connections this is
very useful if you ever plan to stream to a UPNP device over VPN.

## Tested devices ##

_pulseaudio-dlna_ was successfully tested on the follwing devices / applications:

- D-Link DCH-M225/E
- Cocy UPNP media renderer (https://github.com/mnlipp/CoCy)
- BubbleUPnP (Android App)
- Samsung Smart TV LED60 (UE60F6300)
- Samsung Smart TV LED40 (UE40ES6100)
- Xbmc / Kodi

## Supported encoders ##

_pulseaudio-dlna_ supports the following encoders:

- __lame__  MPEG Audio Layer III (MP3)
- __ogg__   Ogg Vorbis
- __flac__  Free Lossless Audio Codec (FLAC)
- __wav__   Waveform Audio File Format (WAV)
