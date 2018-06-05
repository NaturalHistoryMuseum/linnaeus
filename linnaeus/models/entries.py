import os
import re
from io import BytesIO

import requests
from PIL import Image


class BaseEntry(object):
    def __init__(self, key):
        self._key = key

    @property
    def entry(self):
        return self._key

    def __str__(self):
        return str(self._key)

    def validate(self):
        return True

    def __ge__(self, other):
        return str(self) >= str(other)

    def __le__(self, other):
        return str(self) <= str(other)

    def __gt__(self, other):
        return str(self) > str(other)

    def __lt__(self, other):
        return str(self) < str(other)

    def __eq__(self, other):
        return str(self) == str(other)

    def __hash__(self):
        return self._key.__hash__()


class CoordinateEntry(BaseEntry):
    def __init__(self, x, y):
        super(CoordinateEntry, self).__init__(x * y)
        self.x = x
        self.y = y

    def __str__(self):
        return f'{self.x}|{self.y}'

    def validate(self):
        return isinstance(self.x, int) and isinstance(self.y, int) and self._key == (
                self.x * self.y)


class LocationEntry(BaseEntry):
    def __init__(self, path, path_type=None, target=None):
        super(LocationEntry, self).__init__(path)
        self.path = path
        if path_type is not None:
            self._type = path_type
        else:
            if re.match('http.*', path):
                self._type = 'url'
            else:
                self._type = 'local'
        self.target = target

    @property
    def entry(self):
        if self._type == 'url':
            try:
                r = requests.get(self.path, timeout=10)
                return Image.open(BytesIO(r.content))
            except requests.ReadTimeout:
                raise AttributeError(f'Unable to retrieve content: {self.path}')
        elif self._type == 'local':
            if os.path.exists(self.path):
                Image.open(self.path)
            else:
                raise AttributeError(f'File does not exist: {self.path}')
        else:
            raise AttributeError(f'No type found: {self.path}')

    def validate(self):
        return self._type is not None


class HsvEntry(object):
    def __init__(self, hue, saturation, value):
        self.h = hue
        self.s = saturation
        self.v = value

    @property
    def entry(self):
        return self.h, self.s, self.v

    def validate(self):
        return 0 <= self.h <= 255 and 0 <= self.s <= 255 and 0 <= self.v <= 255

    def _diff(self, other):
        h = (self.h - other.h) if other.h is not None else 0
        s = (self.s - other.s) if other.s is not None else 0
        v = (self.v - other.v) if other.v is not None else 0
        if h == s:
            s *= 0.99
        if h == v:
            v *= 0.99
        if s == v:
            v *= 0.99
        return h + s + v

    def __ge__(self, other):
        return self._diff(other) >= 0

    def __le__(self, other):
        return self._diff(other) <= 0

    def __gt__(self, other):
        return self._diff(other) > 0

    def __lt__(self, other):
        return self._diff(other) < 0

    def __eq__(self, other):
        return (self.h == other.h) and (self.s == other.s) and (self.v == other.v)

    def __hash__(self):
        return (self.h, self.s, self.v).__hash__()

    def __str__(self):
        return f'{self.h},{self.s},{self.v}'

    def __sub__(self, other):
        h_diff = abs(self.h - other.h)
        s_diff = abs(self.s - other.s)
        v_diff = abs(self.v - other.v)
        return h_diff + s_diff + v_diff
