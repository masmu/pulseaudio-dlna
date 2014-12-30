import setuptools


setuptools.setup(
    name="pulseaudio-dlna",
    version="0.1",
    py_modules=[
        "pulseaudio_dlna",
        "pulseaudio",
    ],
    packages=[
        "upnp",
    ],
    install_requires=[
        "beautifulsoup",
        "docopt",
    ],
    entry_points={
        "console_scripts": [
            "pulseaudio-dlna = pulseaudio_dlna:main",
        ]
    },
)
