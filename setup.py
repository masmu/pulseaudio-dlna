#!/usr/bin/python3

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
        "Programming Language :: Python :: 3",
        "Environment :: Console",
        "Topic :: Multimedia :: Sound/Audio",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
    version='0.6.0',
    py_modules=[],
    packages=setuptools.find_packages(),
    install_requires=[
        "docopt >= 0.6.1",
        "requests >= 2.2.1",
        "setproctitle >= 1.1.10",
        "notify2 >= 0.3",
        "psutil >= 5.4.7",
        "chardet >= 3.0.4",
        "pyroute2 >= 0.3.5",
        "netifaces >= 0.10.0",
        "lxml >= 3",
        "pychromecast >= 2.3.0",
        "PyGObject >= 3.3.0",
        "dbus-python >= 1.0.0",
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
        "pulseaudio_dlna": ["images/*.png"],
    }
)
