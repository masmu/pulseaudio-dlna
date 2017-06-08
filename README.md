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
