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

import functools
import logging
import inspect
import sys

logger = logging.getLogger('pulseaudio_dlna.rules')

RULES = {}


class RuleNotFoundException(Exception):
    def __init__(self, identifier):
        Exception.__init__(
            self,
            'You specified an invalid rule identifier "{}"!'.format(identifier)
        )


@functools.total_ordering
class BaseRule(object):
    def __str__(self):
        return self.__class__.__name__

    def __eq__(self, other):
        if type(other) is type:
            return type(self) is other
        try:
            if isinstance(other, str):
                return type(self) is RULES[other]
        except Exception:
            raise RuleNotFoundException(other)
        return type(self) is type(other)

    def __gt__(self, other):
        if type(other) is type:
            return type(self) > other
        try:
            if isinstance(other, str):
                return type(self) > RULES[other]
        except Exception:
            raise RuleNotFoundException()
        return type(self) > type(other)

    def to_json(self):
        attributes = []
        d = {
            k: v for k, v in iter(self.__dict__.items())
            if k not in attributes
        }
        d['name'] = str(self)
        return d


class FAKE_HTTP_CONTENT_LENGTH(BaseRule):
    pass


class DISABLE_DEVICE_STOP(BaseRule):
    pass


class DISABLE_MIMETYPE_CHECK(BaseRule):
    pass


class DISABLE_PLAY_COMMAND(BaseRule):
    pass


class REQUEST_TIMEOUT(BaseRule):
    def __init__(self, timeout=None):
        self.timeout = float(timeout or 10)

    def __str__(self):
        return '{} (timeout="{}")'.format(
            self.__class__.__name__, self.timeout)


# class EXAMPLE_PROPERTIES_RULE(BaseRule):
#     def __init__(self, prop1=None, prop2=None):
#         self.prop1 = prop1 or 'abc'
#         self.prop2 = prop2 or 'def'

#     def __str__(self):
#         return '{} (prop1="{}",prop2="{}")'.format(
#             self.__class__.__name__, self.prop1, self.prop2)


class Rules(list):
    def __init__(self, *args, **kwargs):
        list.__init__(self, ())
        self.append(*args)

    def append(self, *args):
        for arg in args:
            if type(arg) is list:
                for value in arg:
                    self.append(value)
            elif type(arg) is dict:
                try:
                    name = arg.get('name', 'missing')
                    rule = RULES[name]()
                except KeyError:
                    raise RuleNotFoundException(name)
                attributes = ['name']
                for k, v in arg.items():
                    if hasattr(rule, k) and k not in attributes:
                        setattr(rule, k, v)
                self._add_rule(rule)
            elif isinstance(arg, str):
                try:
                    rule = RULES[arg]()
                    self._add_rule(rule)
                except KeyError:
                    raise RuleNotFoundException(arg)
            elif isinstance(arg, BaseRule):
                self._add_rule(arg)
            else:
                raise RuleNotFoundException('?')

    def _add_rule(self, rule):
        if rule not in self:
            list.append(self, rule)

    def to_json(self):
        return [rule.to_json() for rule in self]


def load_rules():
    if len(RULES) == 0:
        logger.debug('Loaded rules:')
        for name, _type in inspect.getmembers(sys.modules[__name__]):
            if inspect.isclass(_type) and issubclass(_type, BaseRule):
                if _type is not BaseRule:
                    logger.debug('  {} = {}'.format(name, _type))
                    RULES[name] = _type
    return None


load_rules()
