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

import os
import re
import setuptools


def get_version():
    path = os.path.abspath(os.path.dirname(__file__))
    path = os.path.join(path, "debian", "changelog")
    ex = r"pulseaudio-dlna \((\d+\.\d+\.\d+)\) .*$"
    with open(path) as f:
        releases = f.readlines()
        releases = [re.match(ex, i) for i in releases]
        releases = [i.group(1) for i in releases if i]
    return releases[0]

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
    version=get_version(),
    py_modules=[],
    packages=setuptools.find_packages(),
    install_requires=[
        "BeautifulSoup >= 3.2.1",
        "docopt >= 0.6.1",
        "requests >= 2.2.1",
        "setproctitle >= 1.0.1",
        "protobuf >= 2.5.0",
        "notify2 >= 0.3",
        "psutil >= 1.2.1",
        "futures >= 2.1.6",
    ],
    entry_points={
        "console_scripts": [
            "pulseaudio-dlna = pulseaudio_dlna.__main__:main",
        ]
    },
    data_files=[
        ("share/man/man1", ["debian/pulseaudio-dlna.1"]),
    ],
    package_data={
        "pulseaudio_dlna.plugins.upnp": ["xml/*.xml"],
    }
)
