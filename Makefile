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

python ?= python3
user ?= $(shell whoami)

all: pulseaudio_dlna.egg-info

venv:
	@echo "venv is deprecated. It is just 'make' now."

pulseaudio_dlna.egg-info: setup.py bin/pip
	bin/pip install --editable . && touch $@
bin/pip:
	virtualenv --system-site-packages -p $(python) .

ifdef DEB_HOST_ARCH
DESTDIR ?= /
PREFIX ?= usr/
install:
	$(python) setup.py install --no-compile --prefix="$(PREFIX)" --root="$(DESTDIR)" --install-layout=deb
else
DESTDIR ?= /
PREFIX ?= /usr/local
install:
	$(python) setup.py install --no-compile --prefix="$(PREFIX)"
endif

release: manpage
	pdebuild --buildresult dist
	lintian --pedantic dist/*.deb dist/*.dsc dist/*.changes
	sudo chown -R $(user) dist/

manpage: man/pulseaudio-dlna.1

man/pulseaudio-dlna.1: pulseaudio_dlna.egg-info
	export USE_PKG_VERSION=1; help2man -n "Stream audio to DLNA devices and Chromecasts" "bin/pulseaudio-dlna" > /tmp/pulseaudio-dlna.1
	mv /tmp/pulseaudio-dlna.1 man/pulseaudio-dlna.1

clean:
	rm -rf build dist $(shell find pulseaudio_dlna -name "__pycache__")
	rm -rf *.egg-info *.egg bin local lib lib64 include share pyvenv.cfg
	rm -rf docs htmlcov .coverage .tox pip-selfcheck.json
