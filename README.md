# About #
<img align="left" src="samples/images/application.png">

This is _pulseaudio-dlna_. A lightweight streaming server which brings DLNA / UPNP
and Chromecast support to PulseAudio and Linux.
It can stream your current PulseAudio playback to different UPNP devices
(UPNP Media Renderers) or Chromecasts in your network.
Its main goals are: easy to use, no configuration hassle, no
big dependencies.

UPNP renderers in your network will show up as pulseaudio sinks.

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

 * __master__ - (_2017-04-06_)
    - Fixed a bug where the detection of DLNA devices failed when there were multiple network interfaces
    - The application now binds to all interfaces by default
    - When using multiple network interfaces the appropriate network address is being used for streaming (new dependency `python-pyroute2` (preferred) or `python-netaddr` (fallback))
    - Migrated to GI bindings (removed dependencies `python-gobject` `python-rsvg` `python-gtk2`, new dependency `python-gi`, new optional dependencies `gir1.2-rsvg-2.0`, `gir1.2-gtk-3.0`)
    - Fixed a bug where devices with the same name could keep updating each other
    - Fixed a bug where codec bit rates could not be set although those were supported
    - Fixed a bug where a missing xml attribute prevented xml parsing
    - Added the `--disable-mimetype-check` option
    - Disabled mimetype check for virtual _Raumfeld_ devices
    - Subprocesses now always exit gracefully
    - Added the `--chunk-size` option
    - Added _pulseaudio_ as an encoder backend (*experimental*)
    - You can now just start one instance of pulseaudio-dlna
    - Fixed a bug where non-ascii characters in $PATH broke `distutils.spawn.find_executable()`
    - Also use environment's `XDG_RUNTIME_DIR` for detecting the DBus socket
    - The detection of the stream servers host address now uses the systems routing table
    - Because of devices with a kernel < 3.9, `python-zeroconf >= 0.17.4` is now required

 * __0.5.2__ - (_2016-04-01_)
    - Catched an exception when record processes cannot start properly

 * __0.5.1__ - (_2016-04-01_)
    - Fixed the `--filter-device` option
    - Prioritize _mp3_ over _flac_ for Chromecasts

 * __0.5.0.1__ - (_2016-03-09_)
    - Readded manpage

 * __0.5.0__ - (_2016-03-09_)
    - Set Yamaha devices to the appropriate mode before playing (thanks to [hlchau](https://github.com/hlchau)) (new dependency: `python-lxml`)
    - Fixed a bug where some SSDP messages could not get parsed correctly
    - Also support media renderers identifying as `urn:schemas-upnp-org:device:MediaRenderer:2`
    - Added the `--disable-workarounds` flag
    - Added the `--auto-reconnect` flag
    - Added the `--encoder-backend` option (new optional dependencies `ffmpeg`, `libav-tools`)
    - Removed shared encoder processes
    - Increased the default HTTP timeout to 15 seconds
    - Fixed a bug where manually added renderers could appear twice
    - Added device state polling for devices which start playing on their own
    - Added the flac encoder for _Google Chromecast_
    - Added support for _Google Cast Groups_ (new dependency `python-zeroconf`)
    - Removed dependency `python-beautifulsoup`
    - Fixed a bug where bytes were not decoded properly to unicode

 * __0.4.7__ - (_2015-11-18_)
    - The application can now co-exist with other applications which are using the port 1900/udp (thanks to [klaernie](https://github.com/klaernie))
    - Fixed the daemon mode to support `psutil` 1.x and 2.x (thanks to [klaernie](https://github.com/klaernie))
    - HTML entities in device descriptions are now converted automatically
    - Faster and more reliable device discovery (new dependency `python-netifaces`)
    - Added the `--cover-mode` option, one mode requires (optional) dependencies `gtk`, `cairo`, `rsvg`
    - L16 codecs are now selected better (e.g. needed for _XBox 360_)
    - Fixed a bug where sometimes it was tried to remove sinks twice on cleanup
    - Added the `--update-device-config` flag
    - Added the `--ssdp-ttl`, `--ssdp-mx`, `--ssdp-amount` options
    - Added the `--msearch-port` option

 * __0.4.6__ - (_2015-10-17_)
    - Added support for _Google Chromecast Audio_ (thanks to [leonhandreke](https://github.com/leonhandreke))
    - Fixed a bug where devices which does not specifiy control urls made the application crash
    - Added the `--disable-device-stop` flag
    - Added the `--request-timeout` option
    - You can now also add rules to renderers (e.g. `DISABLE_DEVICE_STOP`, `REQUEST_TIMEOUT`)
    - Fixed a bug where stream urls where not parsed correctly
    - Fixed a bug which made a Chomecast Audio throwing exceptions while stopping
    - Fixed a bug where the system's default encoding could not be determined when piping the applications output

 * __0.4.5.2__ - (_2015-09-21_)
    - Fixed a bug where the encoding of SSDP headers was not detected correctly (new dependency: `python-chardet`)

 * __0.4.5.1__ - (_2015-09-20_)
    - Added a missing dependency `python-concurrent.futures` (thanks to [Takkat-Nebuk](https://github.com/Takkat-Nebuk))

 * __0.4.5__ - (_2015-09-20_)
    - Exceptions while updating sink and device information from pulseaudio are now handled better
    - Changed `--fake-http10-content-length` flag to `--fake-http-content-length` to also support HTTP 1.1 requests
    - Fixed a bug where the supported device mime types could not get parsed correctly
    - Fixed a bug where the device UUID was not parsed correctly
    - Fixed a bug where just mime types beginning with `audio/` where accepted, but not e.g. `application/ogg`
    - The stream server will now respond with 206 when receiving requests with `range` header
    - UPNP control commands have now a timeout of 10 seconds
    - Fixed a bug where the wrong stream was removed from the stream manager
    - Fixed several bugs caused by purely relying on stopping actions for the devices idle state
    - Added L16 Encoder
    - The encoder option can now handle multiple options separated by comma
    - Added the `--create-device-config` flag
    - Fixed a bug where the dbus session was bound from the wrong process
    - Fix a bug where the wrong device UDN was retrieved from XML documents containing multiple devices

 * __0.4.4__ - (_2015-08-07_)
    - Added `--disable-ssdp-listener` option
    - Fixed a bug with applications which remove and re-add streams all the time
    - Added a missing dependency `python-psutil`

 * __0.4.3__ - (_2015-08-02_)
    - Fixed a bug when trying to terminate an encoder process
    - Catch exceptions when trying to update pulseaudio sinks
    - Fixed a timing issue where the streamserver was not ready but devices were already instructed to play

 * __0.4.2__ - (_2015-08-02_)
    - The mp3 encoder is now prioritize over wav
    - Added `--disable-switchback` option
    - Wav encoders do not longer share their encoder process

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
- 17.04 (Zesty Zapus)
- 16.10 (Yakkety Yak)
- 16.04 (Xenial Xerus)
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
- Fedora - RHEL - CentOS - EPEL
    [https://copr.fedoraproject.org/coprs/cygn/pulseaudio-dlna/](https://copr.fedoraproject.org/coprs/cygn/pulseaudio-dlna/)
- Debian
    [https://packages.debian.org/sid/pulseaudio-dlna](https://packages.debian.org/sid/pulseaudio-dlna)

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
- python-docopt
- python-requests
- python-setproctitle
- python-gi
- python-protobuf
- python-notify2
- python-psutil
- python-concurrent.futures
- python-chardet
- python-netifaces
- python-pyroute2 | python-netaddr
- python-lxml
- python-zeroconf
- vorbis-tools
- sox
- lame
- flac
- faac
- opus-tools

You can install all the dependencies in Ubuntu via:

    sudo apt-get install python2.7 python-pip python-setuptools python-dbus python-docopt python-requests python-setproctitle python-gi python-protobuf python-notify2 python-psutil python-concurrent.futures python-chardet python-netifaces python-pyroute2 python-netaddr python-lxml python-zeroconf vorbis-tools sox lame flac faac opus-tools

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

Since 0.4, new devices are automatically discovered as they appear on the network.

### CLI ###

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

### Device configuration rules

Most times the automatic discovery of supported device codecs and their
prioritization works pretty good. But in the case of a device which does work
out of the box or if you don't like the used codec you can adjust the settings
with a _device configuration_.

If you want to create a specific configuration for your devices you can do
that via the `--create-device-config` flag. It will search for devices on
your network and write a config for them. It will look for / write them at:

- `~/.local/share/pulseaudio-dlna/devices.json` (prioritized)
- `/etc/pulseaudio-dlna/devices.json`

The purpose of this is that the application should do the most work for the
user. You just have to edit the file instead of writing it completely on
your own.

Let's make an example:
I started the application via `pulseaudio-dlna --create-device-config` and
that is what was discovered:

```json
    "uuid:e4572d54-c2c7-d491-1eb3-9cf17cf5fe01": {
        "rules": [],
        "flavour": "DLNA",
        "name": "Device name",
        "codecs": [
            {
                "rules": [],
                "bit_rate": null,
                "identifier": "mp3",
                "mime_type": "audio/mpeg"
            },
            {
                "rules": [],
                "identifier": "flac",
                "mime_type": "audio/flac"
            },
            {
                "channels": 2,
                "rules": [],
                "identifier": "l16",
                "sample_rate": 48000,
                "mime_type": "audio/L16;rate=48000;channels=2"
            },
            {
                "channels": 2,
                "rules": [],
                "identifier": "l16",
                "sample_rate": 44100,
                "mime_type": "audio/L16;rate=44100;channels=2"
            },
            {
                "channels": 1,
                "rules": [],
                "identifier": "l16",
                "sample_rate": 44100,
                "mime_type": "audio/L16;rate=44100;channels=1"
            }
        ]
    }
```

It was detected that the device supports the following codecs:

- `audio/mp3`
- `audio/flac`
- `audio/L16;rate=48000;channels=2`
- `audio/L16;rate=44100;channels=2`
- `audio/L16;rate=44100;channels=1`

If you don't change the configuration at all, it means that the next time
you start _pulseaudio-dlna_ it will automatically use those codecs for that
device. The order of the list also defines the priority. It will take the
first codec and use it if the appropriate encoder binary is installed on your
system. If the binary is missing it will take the next one. So here the
_mp3_ codec would be used, if the _lame_ binary is installed.

You can also change the name of the device, adjust the mime type or set the
bit rate.  A `null` value means _default_, for bit rates this
is set to 192 Kbit/s.

In that case I want to rename my device to "Living Room". Besides that
I don't want the L16 codecs, so i simply remove them and i want my _mp3_ to
be encoded in 256 Kbit/s.

```json
    "uuid:e4572d54-c2c7-d491-1eb3-9cf17cf5fe01": {
        "rules": [],
        "flavour": "DLNA",
        "name": "Living Room",
        "codecs": [
            {
                "rules": [],
                "bit_rate": 256,
                "identifier": "mp3",
                "mime_type": "audio/mpeg"
            },
            {
                "rules": [],
                "identifier": "flac",
                "mime_type": "audio/flac"
            }
        ]
    }
```
But as it turns out this device has a problem with playing the _mp3_ stream
when you don't specify the `--fake-http-content-length` flag. Let's say _flac_
works without the flag. So, you can add a rule for that to that device.

```json
    "uuid:e4572d54-c2c7-d491-1eb3-9cf17cf5fe01": {
        "rules": [],
        "flavour": "DLNA",
        "name": "Living Room",
        "codecs": [
            {
                "rules": [
                    {
                        "name": "FAKE_HTTP_CONTENT_LENGTH"
                    }
                ],
                "bit_rate": 256,
                "identifier": "mp3",
                "mime_type": "audio/mpeg"
            },
            {
                "rules": [],
                "identifier": "flac",
                "mime_type": "audio/flac"
            }
        ]
    }
```

That's it. _pulseaudio-dlna_ will automatically use that config if you don't
use the `--encoder` or `--bit-rate` options.

## Known Issues ##

- **Distorted sound**

    If you experience distorted sound, try to pause / unpause the playback or
    changing / adjusting the volume. Some encoders handle volume changes
    better than others. The _lame_ encoder handles this by far better than
    most of the other ones.

- **There is a delay about a few seconds**

    Since there is HTTP streaming used for the audio data to transport,
    there is always a buffer involved. This device buffer ensures that even
    if you suffer from a slow network (e.g. weak wifi) small interruptions
    won't affect your playback. On the other hand devices will first start
    to play when this buffer is filled. Most devices do this based on the
    received amount of data. Therefore inefficient codecs such as _wav_ fill
    that buffer much faster than efficient codecs do. The result is a
    noticeable shorter delay in contrast to e.g. _mp3_ or others. Note, that
    in this case your network should be pretty stable, otherwise your device
    will quickly run out of data and stop playing. This is normally not a
    problem with cable connections. E.g. I have a delay about 1-2 seconds
    with _wav_ and a delay of about 5 seconds with _mp3_ with the same
    cable connected device. You can decrease the delay when using _wav_ or
    using high bit rates, but you won't get rid of it completely.
    My advice: If you have a reliable network, use _wav_. It is lossless
    and you will get a short delay. If you have not, use another encoder
    which does not require that much bandwidth to make sure your device
    will keep playing. Of course you will be affected from a higher delay.

## Troubleshooting ##

- **My device does not get discovered by _pulseaudio-dlna_**

    The computer _pulseaudio-dlna_ is running on and your device needs to be in
    the same network. In uncomplicated home LANs this is normally the case.
    You can test if other applications are able to find your device,
    e.g. _BubbleUPnP_ (_Android_ application). If they do it is likely that
    you are using a firewall / iptables. Try disabling it. If you verified that
    your firewall is blocking, you should use the `--msearch-port <port>`
    option and open port 8080/_tcp_, port 1900/_udp_ and port `<port>`/_udp_.

- **The device is successfully instructed to play, but the device never
    connects to _pulseaudio-dlna_**

    Check if your are using a firewall / iptables. If that works, open
    port 8080/_tcp_ and port 1900/_udp_.

- **The device is successfully instructed to play, but the device immediately
    disconnects after some seconds**

    Some devices do not stick to the HTTP 1.0/1.1 standard. Since most devices
    do, _pulseaudio-dlna_ must be instructed by CLI flags to act in a
    non-standard way.

    - `--fake-http-content-length`

        Adds a faked HTTP Content-Length to HTTP 1.0/1.1 responses. The length
        is set to 100 GB and ensures that the device would keep playing for
        months. This is e.g. necessary for the _Hame Soundrouter_ and depending
        on the used encoder for _Sonos_ devices.

## Tested devices ##

A listed entry means that it was successfully tested, even if there is no specific
codec information available.

Device                                                                          | mp3                               | wav                               | ogg                               | flac                              | aac                               | opus                              | l16
------------- | ------------- | ------------- | ------------- | ------------- | ------------- | ------------- | -------------
[AVM FritzRepeater N/G](http://avm.de/)                                         | :white_check_mark:                | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
BubbleUPnP (Android App)                                                        | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :no_entry_sign:                   | :white_check_mark:
[Cocy UPNP media renderer](https://github.com/mnlipp/CoCy)                      | :white_check_mark:                | :no_entry_sign:                   | :white_check_mark:                | :no_entry_sign:                   | :no_entry_sign:                   | :no_entry_sign:                   | :no_entry_sign:
D-Link DCH-M225/E                                                               | :white_check_mark:                | :white_check_mark:                | :no_entry_sign:                   | :white_check_mark:                | :white_check_mark:                | :no_entry_sign:                   | :no_entry_sign:
DAMAI Airmusic                                                                  | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Denon AVR-3808                                                                  | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Denon AVR-X4000                                                                 | :white_check_mark:                | :grey_question:                   | :grey_question:                   | :white_check_mark:                | :grey_question:                   | :grey_question:                   | :grey_question:
Freebox Player Mini (4K)                                                        | :white_check_mark:                | :no_entry_sign:                   | :no_entry_sign:                   | :white_check_mark:                | :white_check_mark:                | :no_entry_sign:                   | :no_entry_sign:
Freebox Player (Revolution)                                                     | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :no_entry_sign:                   | :no_entry_sign:                   | :no_entry_sign:
[gmrender-resurrect](http://github.com/hzeller/gmrender-resurrect)              | :white_check_mark:                | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Google Chromecast (1st gen)                                                     | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :no_entry_sign:                   | :no_entry_sign:
Google Chromecast Audio                                                         | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                   | :white_check_mark:                | :no_entry_sign:                   | :no_entry_sign:
Hame Soundrouter                                                                | :white_check_mark:<sup>1</sup>    | :no_entry_sign:                   | :no_entry_sign:                   | :white_check_mark:<sup>1</sup>    | :no_entry_sign:                   | :no_entry_sign:                   | :no_entry_sign:
LG BP550                                                                        | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Libratone ZIPP                                                                  | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :no_entry_sign:                   | :no_entry_sign:                   | :white_check_mark:
Logitech Media Server                                                           | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Majik DSM                                                                       | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Medion P85055                                                                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
[Naim Mu-So](https://www.naimaudio.com/mu-so)                                                        | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :grey_question:                | :grey_question:                   | :white_check_mark:
Onkyo TX-8050                                                                   | :white_check_mark:                | :white_check_mark:                | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :white_check_mark:
Onkyo TX-NR509                                                                  | :grey_question:                   | :white_check_mark:                | :grey_question:                   | :no_entry_sign:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Onkyo TX-NR616 <sup>7</sup>                                                     | :grey_question:                   | :white_check_mark:                | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Onkyo TX-NR646                                                                  | :white_check_mark:                | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Onkyo TX-NR727 <sup>7</sup>                                                     | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Onkyo CR-N755                                                                   | :white_check_mark:<sup>8</sup>    | :white_check_mark:                | :no_entry_sign:                   | :no_entry_sign:                   | :grey_question:<sup>9</sup>       | :no_entry_sign:                   | :white_check_mark:
[Oppo Sonica](https://www.oppodigital.com/sonica/)                                                                   | :white_check_mark:    | :no_entry_sign:                | :no_entry_sign:                   | :white_check_mark:                   | :white_check_mark:       | :grey_question:                   | :white_check_mark:
[Pi MusicBox](http://www.woutervanwijk.nl/pimusicbox/)                          | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Panasonic TX-50CX680W                                                           | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Panasonic TX-50CX680W                                                           | :white_check_mark:                | :white_check_mark:                | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Philips NP2500                                                                  | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Philips NP2900                                                                  | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Pioneer SC-LX76 (AV Receiver)                                                   | :white_check_mark:                | :white_check_mark:                | :no_entry_sign:                   | :no_entry_sign:                   | :no_entry_sign:                   | :no_entry_sign:                   | :white_check_mark:
Pioneer VSX-824 (AV Receiver)                                                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Pure Jongo S3                                                                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
[Raumfeld One M](http://raumfeld.com)                                           | :white_check_mark:                | :white_check_mark:                | :no_entry_sign:                   | :white_check_mark:                | :grey_question:                   | :no_entry_sign:                   | :no_entry_sign:
[Raumfeld Speaker M](http://raumfeld.com)                                       | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
[Raumfeld Speaker S](http://raumfeld.com)                                       | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :grey_question:                   | :grey_question:                   | :grey_question:
[ROCKI](http://www.myrocki.com/)                                                | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
[rygel](https://wiki.gnome.org/Projects/Rygel)                                  | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
RaidSonic IB-MP401Air                                                           | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Samsung Smart TV LED32 (UE32ES5500)                                             | :white_check_mark:                | :no_entry_sign:                   | :white_check_mark:                | :white_check_mark:                | :no_entry_sign:                   | :no_entry_sign:                   | :no_entry_sign:
Samsung Smart TV LED40 (UE40ES6100)                                             | :white_check_mark:                | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Samsung Smart TV LED46 (UE46ES6715)                                             | :white_check_mark:                | :no_entry_sign:                   | :white_check_mark:                | :white_check_mark:                | :no_entry_sign:                   | :grey_question:                   | :no_entry_sign:
Samsung Smart TV LED48 (UE48JU6560)                                             | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :white_circle:<sup>2</sup>        | :no_entry_sign:                   | :no_entry_sign:
Samsung Smart TV LED60 (UE60F6300)                                              | :white_check_mark:                | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Sonos PLAY:1                                                                    | :white_check_mark:<sup>3</sup>    | :white_check_mark:                | :white_check_mark:<sup>3</sup>    | :white_check_mark:                | :no_entry_sign:                   | :no_entry_sign:                   | :grey_question:
Sonos PLAY:3                                                                    | :white_check_mark:<sup>3</sup>    | :white_check_mark:                | :white_check_mark:<sup>3</sup>    | :white_check_mark:                | :no_entry_sign:                   | :no_entry_sign:                   | :grey_question:
Sony SRS-X77                                                                    | :white_check_mark:<sup>1</sup>    | :no_entry_sign:                   | :no_entry_sign:                   | :no_entry_sign:                   | :no_entry_sign:                   | :no_entry_sign:                   | :white_check_mark:<sup>1</sup>
Sony SRS-X88                                                                    | :white_check_mark:<sup>1</sup>    | :no_entry_sign:                   | :no_entry_sign:                   | :no_entry_sign:                   | :no_entry_sign:                   | :no_entry_sign:                   | :white_check_mark:<sup>1</sup>
Sony SRS-ZR5                                                                    | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :no_entry_sign:                   | :no_entry_sign:
Sony STR-DN1050 (AV Receiver)                                                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
[Volumio](http://volumio.org)                                                   | :white_check_mark:                | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
[Volumio 2](http://volumio.org)                                                 | :white_check_mark:                | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Xbmc / Kodi                                                                     | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :white_check_mark:                | :white_circle:<sup>2</sup>        | :white_circle:<sup>2</sup>        | :white_check_mark:
Xbox 360                                                                        | :white_check_mark:<sup>5</sup>    | :no_entry_sign:                   | :no_entry_sign:                   | :no_entry_sign:                   | :grey_question:                   | :no_entry_sign:                   | :white_check_mark:
Yamaha CRX-N560D <sup>4</sup>                                                   | :white_check_mark:                | :no_entry_sign:                   | :no_entry_sign:                   | :no_entry_sign:                   | :no_entry_sign:                   | :no_entry_sign:                   | :white_check_mark:
Yamaha RX-475 (AV Receiver)                                                     | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
Yamaha RX-V573 (AV Receiver) <sup>6</sup>                                       | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:
WDTV Live                                                                       | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:                   | :grey_question:

<sup>1</sup>) Works when specifing the `--fake-http-content-length` flag

<sup>2</sup>) Is capable of playing the codec, but does not specifiy the correct mime type

<sup>3</sup>) Works since _0.4.5_ (`--fake-http-content-length` is added automatic)

<sup>4</sup>) The device needs to be in _SERVER_ mode to accept instructions

<sup>5</sup>) Was reported to buffer really long. Approximately 45 seconds

<sup>6</sup>) Was reported to have issues being discovered. Make sure you run the latest firmware

<sup>7</sup>) Reported to need a `--request-timeout` of 15 seconds to work. Since _0.5.0_ the timeout is set to that value.

<sup>8</sup>) Stuttering at 256kbit/s and pretty unstable at 320kbit/s

<sup>9</sup>) The manual states it is supported. No success yet, neither with --fake-http-content-length nor with increased timeout values

## Supported encoders ##

Encoder     | Description                       | Identifier
------------- | ------------- | -------------
lame        | MPEG Audio Layer III              | mp3
oggenc      | Ogg Vorbis                        | ogg
flac        | Free Lossless Audio Codec         | flac
sox         | Waveform Audio File Format        | wav
opusenc     | Opus Interactive Audio Codec      | opus
faac        | Advanced Audio Coding             | aac
sox         | Linear PCM                        | l16

You can select a specific codec using the `--encoder` flag followed by its identifier.
