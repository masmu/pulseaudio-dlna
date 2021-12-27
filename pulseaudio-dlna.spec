%global srcname pulseaudio_dlna

Name: pulseaudio-dlna
Version: 0.6.3
Release: 4
Source0: %{name}-%{version}.tar.gz
License: GPLv3
Group: Development/Libraries
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot
Prefix: %{_prefix}
BuildArch: noarch
Vendor: Massimo Mund <mo@lancode.de>
Url: https://github.com/cygn/pulseaudio-dlna
Packager: Sinan H <sinan@haliyo.net>
Summary: A small DLNA server which brings DLNA / UPNP support to PulseAudio and Linux.

BuildRequires: 	python3-setuptools
BuildRequires:	python3-pip
BuildRequires:  python3-devel
Requires:       python3-gobject
Requires:	sox
Requires:	vorbis-tools

%description
A small DLNA server which brings DLNA / UPNP support to PulseAudio and Linux.

It can stream your current PulseAudio playback to different UPNP devices (UPNP Media Renderers) in your network. It's main goals are: easy to use, no configuration hassle, no big dependencies.

https://github.com/cygn/pulseaudio-dlna 

%pre
rm -rf %{python3_sitelib}/%{srcname}*

%prep
%autosetup -n %{name}-%{unmangled_version}

%build
%py3_build

%install
%py3_install

%clean
rm -rf $RPM_BUILD_ROOT

# Note that there is no %%files section for the unversioned python module
%files -n %{name} 
%doc README.md
%license LICENSE
%{python3_sitelib}/%{srcname}-*.egg-info/ 
%{python3_sitelib}/%{srcname}/
%{_bindir}/pulseaudio-dlna
%{_mandir}/man1/%{name}.1*

%changelog
* Mon Dec 27 2021 Sinan Haliyo <sinan.haliyo@upmc.fr> 0.6.3-4
- new release (sinan.haliyo@upmc.fr)

* Mon Dec 27 2021 Sinan Haliyo <sinan.haliyo@upmc.fr> 0.6.3-3
- new package built with tito

* Mon Dec 27 2021 Sinan Haliyo <sinan.haliyo@upmc.fr>
- new package built with tito



