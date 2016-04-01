#!/usr/bin/python

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

import setuptools


setuptools.setup(
    name="pulseaudio-dlna",
    author="Massimo Mund",
    author_email="mo@lancode.de",
    url="https://github.com/masmu/pulseaudio-dlna",
    description="A small DLNA server which brings DLNA / UPNP support"
                "to PulseAudio and Linux.",
    license="GPLv3",
    platforms="Debian GNU/Linux",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Programming Language :: Python :: 2.7",
        "Environment :: Console",
        "Topic :: Multimedia :: Sound/Audio",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
    version='0.5.1',
    py_modules=[],
    packages=setuptools.find_packages(),
    install_requires=[
        "docopt >= 0.6.1",
        "requests >= 2.2.1",
        "setproctitle >= 1.0.1",
        "protobuf >= 2.5.0",
        "notify2 >= 0.3",
        "psutil >= 1.2.1",
        "futures >= 2.1.6",
        "chardet >= 2.0.1",
        "netifaces >= 0.8",
        "lxml >= 3",
        "zeroconf >= 0.17",
    ],
    entry_points={
        "console_scripts": [
            "pulseaudio-dlna = pulseaudio_dlna.__main__:main",
        ]
    },
    data_files=[
        ("share/man/man1", ["man/pulseaudio-dlna.1"]),
    ],
    package_data={
        "pulseaudio_dlna.plugins.upnp": ["xml/*.xml"],
        "pulseaudio_dlna": ["images/*.png"],
    }
)
