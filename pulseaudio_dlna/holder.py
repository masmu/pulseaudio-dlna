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

import logging
import threading
import requests
import traceback
import setproctitle
import signal
import time

logger = logging.getLogger('pulseaudio_dlna.holder')


class Holder(object):
    def __init__(
            self, plugins,
            pulse_queue=None, device_filter=None, device_config=None,
            proc_title=None):
        self.plugins = plugins
        self.device_filter = device_filter or None
        self.device_config = device_config or {}
        self.pulse_queue = pulse_queue
        self.devices = {}
        self.proc_title = proc_title
        self.lock = threading.Lock()
        self.__running = True

    def initialize(self):
        signal.signal(signal.SIGTERM, self.shutdown)
        if self.proc_title:
            setproctitle.setproctitle(self.proc_title)

    def shutdown(self, *args):
        if self.__running:
            logger.info('Holder.shutdown()')
            self.__running = False

    def search(self, ttl=None, host=None):
        self.initialize()
        threads = []
        for plugin in self.plugins:
            thread = threading.Thread(
                target=plugin.discover, args=[self],
                kwargs={'ttl': ttl, 'host': host})
            thread.daemon = True
            threads.append(thread)
        try:
            for thread in threads:
                thread.start()
            while self.__running:
                all_dead = True
                time.sleep(0.1)
                for thread in threads:
                    if thread.is_alive():
                        all_dead = False
                        break
                if all_dead:
                    break
        except Exception:
            traceback.print_exc()
        logger.info('Holder.search()')

    def lookup(self, locations):
        self.initialize()
        xmls = {}
        for url in locations:
            try:
                response = requests.get(url, timeout=5)
                logger.debug('Response from device ({url})\n{response}'.format(
                    url=url, response=response.text))
                xmls[url] = response.content
            except requests.exceptions.Timeout:
                logger.warning(
                    'Could no connect to {url}. '
                    'Connection timeout.'.format(url=url))
            except requests.exceptions.ConnectionError:
                logger.warning(
                    'Could no connect to {url}. '
                    'Connection refused.'.format(url=url))

        for plugin in self.plugins:
            for url, xml in list(xmls.items()):
                device = plugin.lookup(url, xml)
                self.add_device(device)

    def add_device(self, device):
        if not device:
            return
        try:
            self.lock.acquire()
            if device.udn not in self.devices:
                if device.validate():
                    config = self.device_config.get(device.udn, None)
                    device.activate(config)
                    if not self.device_filter or \
                       device.name in self.device_filter:
                        if config:
                            logger.info(
                                'Using device configuration:\n{}'.format(
                                    device.__str__(True)))
                        self.devices[device.udn] = device
                        self._send_message('add_device', device)
                    else:
                        logger.info('Skipped the device "{name}" ...'.format(
                            name=device.label))
            else:
                if device.validate():
                    self._send_message('update_device', device)
        finally:
            self.lock.release()

    def remove_device(self, device_id):
        if not device_id or device_id not in self.devices:
            return
        try:
            self.lock.acquire()
            device = self.devices[device_id]
            self._send_message('remove_device', device)
            del self.devices[device_id]
        finally:
            self.lock.release()

    def _send_message(self, _type, device):
        if self.pulse_queue:
            self.pulse_queue.put({
                'type': _type,
                'device': device
            })
