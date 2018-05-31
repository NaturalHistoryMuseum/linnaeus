import json
import abc


class BaseMapKey(object):
    def __init__(self, key):
        self.key = key

    def __str__(self):
        return str(self.key)


class MapValue(object):
    def __init__(self, hue, saturation, value):
        self.h = hue
        self.s = saturation
        self.v = value

    @property
    def entry(self):
        return (self.h, self.s, self.v)

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


class MapRecord(object):
    def __init__(self, key, value):
        self.key = key
        self.value = value

    def __ge__(self, other):
        return self.value >= other.value

    def __le__(self, other):
        return self.value <= other.value

    def __gt__(self, other):
        return self.value > other.value

    def __lt__(self, other):
        return self.value < other.value

    def __eq__(self, other):
        return self.value == other.value


class BaseMap(abc.ABC):
    def __init__(self):
        self._records = []
        self._keys = set()
        self._keytype = None

    def __len__(self):
        return len(self._records)

    @property
    def records(self):
        return sorted(self._records)

    def serialise(self):
        record_dump = {str(r.key): r.value.entry for r in self._records}
        return json.dumps(record_dump)

    @abc.abstractmethod
    def validate(self, record):
        return True

    def add(self, key, h, s, v):
        record_key = BaseMapKey(key)
        record_value = MapValue(h, s, v)
        record = MapRecord(record_key, record_value)
        if self.validate(record):
            self._records.append(record)
            self._keys.add(record.key.key)
