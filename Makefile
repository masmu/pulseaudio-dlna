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

python ?= python2.7
user ?= $(shell whoami)

all: pulseaudio_dlna.egg-info

pulseaudio_dlna.egg-info: setup.py bin/pip
	bin/pip install --editable . && touch $@
bin/pip:
	virtualenv --system-site-packages -p $(python) .

install:
	sudo $(python) setup.py develop
	sudo chown -R $(user) pulseaudio_dlna.egg-info/

uninstall:
	sudo $(python) setup.py develop --uninstall
	sudo rm /usr/local/bin/pulseaudio-dlna || true

release: manpage
	pdebuild --buildresult dist
	lintian --pedantic dist/*.deb dist/*.dsc dist/*.changes
	sudo chown -R $(user) dist/

manpage: debian/pulseaudio-dlna.1

debian/pulseaudio-dlna.1: pulseaudio_dlna.egg-info
	help2man "bin/pulseaudio-dlna" > /tmp/pulseaudio-dlna.1
	mv /tmp/pulseaudio-dlna.1 debian/pulseaudio-dlna.1

ifdef DEB_HOST_ARCH
DESTDIR ?= /
PREFIX ?= usr/
install:
	$(python) setup.py install --no-compile --prefix="$(PREFIX)" --root="$(DESTDIR)" --install-layout=deb
endif

clean:
	rm -rf build dist $(shell find pulseaudio_dlna -name "__pycache__")
	rm -rf *.egg-info *.egg bin local lib lib64 include share pyvenv.cfg
	rm -rf docs htmlcov .coverage .tox pip-selfcheck.json
