# Changelog

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
