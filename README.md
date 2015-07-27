# About #

This is _pulseaudio-dlna_. A small DLNA server which brings DLNA / UPNP
and Chromecast support to PulseAudio and Linux.

It can stream your current PulseAudio playback to different UPNP devices
(UPNP Media Renderers) or Chromecasts in your network.
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

 * __0.4.1__ - (_2015-07-27_)
    - Fixed Makefile for launchpad

 * __0.4.0__ - (_2015-07-27_)
    - Added the ```--fake-http10-content-length``` option
    - The application can now run as root
    - Catch pulseaudio exceptions for streams, sinks and modules when those are gone
    - Fixed a bug where a missing ssdp header field made the application crash
    - New devices are added now during runtime (thanks to [coder-hugo](https://github.com/coder-hugo))
    - Rewrite of the streaming server
    - Upnp devices can now request their audio format based on their capabilities
    - Added AAC encoder
    - If a device stops playing, the streams currently playing on
      the corresponding sink are switched back to the default sink
    - If a device failes to start playing, streams currently playing on
      the corresponding sink are switched back to the default sink
    - Added Chromecast support (new dependency: `python-protobuf`)
    - Fixed a bug where the application crashed when there was no suitable encoder found
    - Added the ```--bit-rate``` option
    - Added additional headers for DLNA devices
    - Added switch back mode also for sinks, not just for streams (new dependency: `python-notify2`)
    - Added better logging
    - Validate encoders for installed dependencies

 * __0.3.5__ - (_2015-04-09_)
    - Fixed a bug where Sonos description XML could not get parsed correctly

 * __0.3.4__ - (_2015-03-22_)
    - Fixed Makefile for launchpad

 * __0.3.3__ - (_2015-03-22_)
    - Added the ```--filter-device``` option
    - Send 2 SSDP packets by default for better UPNP device discovery
    - Added virtualenv for local installation

 * __0.3.2__ - (_2015-03-14_)
    - Added the Opus Encoder (new dependency: `opus-tools`) (thanks to [MobiusHorizons](https://github.com/MobiusHorizons))
    - Fixed a bug where an empty UPNP device name made the application crash
    - Added a missing dependency (`python-gobject`)

 * __0.3.1__ - (_2015-02-13_)
    - Fixed a bug so that AVTransports other than 1 can be used (thanks to [martin-insulander-info](https://github.com/martin-insulander-info))

 * __0.3.0__ - (_2015-02-01_)
    - Added debian packaging
    - Added proper signal handlers (new dependency: `python-setproctitle`)
    - Fixed a bug where binding to an already used port made the application crash
    - HTTP charset encoding is now specified correctly

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

## Installation via PPA ##

Supported Ubuntu releases:
- 15.04 (Vivid Vervet)
- 14.04.2 LTS (Trusty Tahr)

Ubuntu users can install _pulseaudio-dlna_ via the following [repository](https://launchpad.net/~qos/+archive/ubuntu/pulseaudio-dlna).

    sudo apt-add-repository ppa:qos/pulseaudio-dlna
    sudo apt-get update
    sudo apt-get install pulseaudio-dlna

### Starting ###

After that you can start _pulseaudio-dlna_ via:

    pulseaudio-dlna

Head over the the _using section_ for further instructions.

## Installation for other distributions ##

Some community members are providing packages for others distributions.
_Keep in mind that since i am not using those, i can hardly support them!_

- Arch Linux
    [https://aur.archlinux.org/packages/pulseaudio-dlna/](https://aur.archlinux.org/packages/pulseaudio-dlna/)
- openSUSE (_.rpm_)
    [http://packman.links2linux.de/package/pulseaudio-dlna](http://packman.links2linux.de/package/pulseaudio-dlna)


## Installation via git ##

Other linux users can clone this git repository,
make sure you have all the dependencies installed and the PulseAudio DBus module
is loaded.

### Basic requirements ###

These are the requirements _pulseaudio-dlna_ acutally needs to run. These dependencies
will get installed if you install it via the PPA.

- python2.7
- python-pip
- python-setuptools
- python-dbus
- python-beautifulsoup
- python-docopt
- python-requests
- python-setproctitle
- python-gobject
- python-protobuf
- python-notify2
- vorbis-tools
- sox
- lame
- flac
- faac
- opus-tools

You can install all the dependencies in Ubuntu via:

    sudo apt-get install python2.7 python-pip python-setuptools python-dbus python-beautifulsoup python-docopt python-requests python-setproctitle python-gobject python-protobuf python-notify2 vorbis-tools sox lame flac faac opus-tools

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

### Install it local ###

The recommend method of using _pulseaudio-dlna_ is to install it local to a
python _virtualenv_. In that way you will keep your system clean. If you don't like
it anymore, just delete the folder.
For that method you need some additional dependencies.

#### virtualenv requirements ####

- python-virtualenv (Ubuntu <= _14.04 Trusty LTS_)
- virtualenv (Ubuntu >= _14.10 Utopic_)
- python-dev

So all Ubuntu versions prior to _14.10 Utopic_ need to install:

    sudo apt-get install python-virtualenv python-dev

All Ubuntu versions above install:

    sudo apt-get install virtualenv python-dev

#### Installing & starting ####

Change to the _project root folder_ and start the installation via:

    make

After that you can start _pulseaudio-dlna_ via:

    bin/pulseaudio-dlna

### Install it to your system ###

Since some people like it more to install software globally, you can do that too.
In many software projects this is the default installation method.

#### Installing & starting ####

Change to the _root folder_ and start the installation via:

    make install

After that you can start _pulseaudio-dlna_ via:

    pulseaudio-dlna

### Using ###

_pulseaudio-dlna_ should detect the ip address your computer is reachable within
your local area network. If the detected ip address is not correct or there
were no ips found, you still can specifiy them yourself via the host
option (```--host <your-ip>```)

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
        pulseaudio-dlna [--host <host>] [--port <port>] [--encoder <encoder>] [--bit-rate=<rate>] [--filter-device=<filter-device>] [--renderer-urls <urls>] [--debug] [--fake-http10-content-length]
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
        --fake-http10-content-length           If set, the content-length of HTTP 1.0 requests will be set to 100 GB.
        -v --version                           Show the version.
        -h --help                              Show the help.

Samples:
- `pulseaudio-dlna` will start
_pulseaudio-dlna_ on port _8080_ and stream your PulseAudio streams encoded
with _mp3_.
- `pulseaudio-dlna --encoder ogg` will start
_pulseaudio-dlna_ on port _8080_ and stream your PulseAudio streams encoded
with _Ogg Vorbis_.
- `pulseaudio-dlna --port 10291 --encoder flac` will start
_pulseaudio-dlna_ on port _10291_ and stream your PulseAudio streams encoded
with _FLAC_.
- `pulseaudio-dlna --filter-device 'Nexus 5,TV'` will just use devices named
_Nexus 5_ or _TV_ even when more devices got discovered.
- `pulseaudio-dlna --renderer-urls http://192.168.1.7:7676/smp_10_`
won't discover upnp devices by itself. Instead it will search for upnp renderers
at the specified locations. You can specify multiple locations via urls
seperated by comma (_,_). Most users won't ever need this option, but since
UDP multicast packages won't work (most times) over VPN connections this is
very useful if you ever plan to stream to a UPNP device over VPN.

## Troubleshooting ##

Some devices do not stick to the HTTP 1.0/1.1 standard. Since most devices do,
_pulseaudio-dlna_ must be instructed by CLI flags to act in a non-standard way.

- `--fake-http10-content-length`

    Adds a faked HTTP Content-Length to HTTP 1.0 responses. The length is set 
    to 100 GB and ensures that the device would keep playing for months.
    This is necessary for the _Hame Soundrouter_.

## Tested devices ##

_pulseaudio-dlna_ was successfully tested on the follwing devices / applications:

- D-Link DCH-M225/E
- [Cocy UPNP media renderer](https://github.com/mnlipp/CoCy)
- BubbleUPnP (Android App)
- Samsung Smart TV LED60 (UE60F6300)
- Samsung Smart TV LED40 (UE40ES6100)
- Xbmc / Kodi
- Philips Streamium NP2500 Network Player
- Yamaha RX-475 (AV Receiver)
- Majik DSM
- [Pi MusicBox](http://www.woutervanwijk.nl/pimusicbox/)
- Google Chromecast
- Sonos PLAY:1
- Sonos PLAY:3
- Hame Soundrouter
- [Raumfeld Speaker M](http://raumfeld.com)
- Pioneer VSX-824 (AV Receiver)
- [ROCKI] (http://www.myrocki.com/)
- Sony STR-DN1050 (AV Receiver)
- Pure Jongo S3

## Supported encoders ##

_pulseaudio-dlna_ supports the following encoders:

- __lame__  MPEG Audio Layer III (MP3)
- __ogg__   Ogg Vorbis
- __flac__  Free Lossless Audio Codec (FLAC)
- __wav__   Waveform Audio File Format (WAV)
- __opus__  Opus Interactive Audio Codec (OPUS)
- __aac__   Advanced Audio Coding (AAC)
