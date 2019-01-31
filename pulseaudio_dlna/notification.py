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

import notify2

logger = logging.getLogger('pulseaudio_dlna.notification')


def show(title, message, icon=''):
    try:
        notice = notify2.Notification(title, message, icon)
        notice.set_timeout(notify2.EXPIRES_DEFAULT)
        notice.show()
    except Exception:
        logger.info(
            'notify2 failed to display: {title} - {message}'.format(
                title=title,
                message=message))


try:
    notify2.init('pulseaudio_dlna')
except Exception:
    logger.error('notify2 could not be initialized! Notifications will '
                 'most likely not work.')
