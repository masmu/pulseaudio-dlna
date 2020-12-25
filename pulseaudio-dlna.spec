%define name pulseaudio-dlna
%define version 0.6.1
%define unmangled_version 0.6.1
%define unmangled_version 0.6.1
%define release 2

Summary: A small DLNA server which brings DLNA / UPNP support to PulseAudio and Linux.
Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{unmangled_version}.tar.gz
License: GPLv3
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Massimo Mund <mo@lancode.de>
Url: https://github.com/cygn/pulseaudio-dlna
Packager: Sinan H <sinan@haliyo.net>

BuildRequires: 	python3-setuptools
BuildRequires:	python3-pip
Requires:       python3-docopt
Requires:       python3-chardet
Requires:	python3-gobject
Requires: 	python3-dbus
Requires: 	python3-docopt
Requires:	python3-requests
Requires:	python3-setproctitle
Requires:	python3-protobuf
Requires:	python3-lxml
Requires:	python3-netifaces
Requires:	python3-zeroconf
Requires:	python3-urllib3
Requires:	python3-psutil
Requires:	python3-pyroute2
Requires:       python3-chromecast >= 7.5.1
Requires:       python3-notify2
Requires:	sox
Requires:	vorbis-tools

%description
A small DLNA server which brings DLNA / UPNP support to PulseAudio and Linux.

It can stream your current PulseAudio playback to different UPNP devices (UPNP Media Renderers) in your network. It's main goals are: easy to use, no configuration hassle, no big dependencies.

https://github.com/cygn/pulseaudio-dlna 


%prep
%setup -n %{name}-%{unmangled_version} -n %{name}-%{unmangled_version}

%build
python3 setup.py build

%install
python3 setup.py install --single-version-externally-managed -O1 --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

%clean
rm -rf $RPM_BUILD_ROOT

%files -f INSTALLED_FILES
%defattr(-,root,root)
