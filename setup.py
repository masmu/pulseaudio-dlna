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
    maintainer="Sinan H",
    maintainer_email="cygn@lamad.net",
    platforms="GNU/linux",
    url="https://github.com/cygn/pulseaudio-dlna",
    description="A small DLNA server which brings DLNA / UPNP support"
                "to PulseAudio and Linux.",
    license="License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    classifiers=[
        "Development Status :: 6 - Beta",
        "Programming Language :: Python :: 3",
        "Environment :: Console",
        "Topic :: Multimedia :: Sound/Audio",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
    ],
    version='0.6.3',
    py_modules=[],
    packages=setuptools.find_packages(),
    install_requires=[
    'docopt',
    'chardet',
    'dbus-python',
    'docopt',
    'requests',
    'setproctitle',
    'protobuf',
    'lxml',
    'netifaces',
    'zeroconf',
    'urllib3',
    'psutil',
    'pyroute2',
    'notify2',
    'pychromecast>=7',
    ],
    entry_points={
        "console_scripts": [
            "pulseaudio-dlna = pulseaudio_dlna.__main__:main",
        ]
    },
    data_files=[
        ("share/man/man1", ["man/pulseaudio-dlna.1.gz"]),
    ],
    package_data={
        "pulseaudio_dlna": ["images/*.png"],
    }
)
