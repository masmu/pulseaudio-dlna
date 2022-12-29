%global srcname pulseaudio_dlna

Name: pulseaudio-dlna
Version: 0.6.6
Release: 1
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
%autosetup -n %{name}-%{version}

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
* Thu Dec 29 2022 Sinan Haliyo <sinan.haliyo@upmc.fr> 0.6.6-1
- fix processing of dict-encapsulated sink mime support response
  84c60d800a3cc549b5b829b1c599c22fa7b030f1 @stsichler (sinan.haliyo@upmc.fr)

* Sat Mar 19 2022 Sinan Haliyo <sinan.haliyo@upmc.fr> 0.6.5-1
- requires pychromecast 10 (Cygn@users.noreply.github.com)

* Sat Jan 08 2022 Sinan Haliyo <sinan.haliyo@upmc.fr> 0.6.4-1
- pychromecast 10 compatiblity (Cygn@users.noreply.github.com)
- pychromecast 10 compatible now (Cygn@users.noreply.github.com)

* Thu Jan 06 2022 cygn <sinan@lamad.net> 0.6.3-6
- 

* Mon Dec 27 2021 Sinan Haliyo <sinan.haliyo@upmc.fr> 0.6.3-5
- 

* Mon Dec 27 2021 Sinan Haliyo <sinan.haliyo@upmc.fr> 0.6.3-4
- new release (sinan.haliyo@upmc.fr)

* Mon Dec 27 2021 Sinan Haliyo <sinan.haliyo@upmc.fr> 0.6.3-3
- new package built with tito

* Mon Dec 27 2021 Sinan Haliyo <sinan.haliyo@upmc.fr>
- new package built with tito



