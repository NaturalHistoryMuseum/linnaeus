import abc
import json

from .entries import BaseEntry, CoordinateEntry, HsvEntry, LocationEntry


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
    key_type = BaseEntry
    value_type = HsvEntry

    def __init__(self):
        self._records = []
        self._keys = set()

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
        if not isinstance(record.key, self.key_type) or not record.key.validate():
            raise KeyError
        if not isinstance(record.value, self.value_type) or not record.value.validate():
            raise ValueError
        return True

    def add(self, key: BaseEntry, value: BaseEntry):
        record = MapRecord(key, value)
        if self.validate(record):
            self._records.append(record)
            self._keys.add(str(record.key))

    def worker(self, i):
        return self.records[i - 1]

    def task(self, i, workers):
        try:
            return self.records[i - workers - 1]
        except IndexError:
            print(i, workers, len(self.records))
            raise IndexError


class ReferenceMap(BaseMap):
    key_type = CoordinateEntry
    value_type = HsvEntry

    def validate(self, record):
        if str(record.key) in self._keys:
            raise KeyError('Duplicate key')
        return super(ReferenceMap, self).validate(record)

    @property
    def bounds(self):
        return max(self._records, key=lambda x: (x.key.x, x.key.y))


class ComponentMap(BaseMap):
    key_type = LocationEntry
    value_type = HsvEntry

    def validate(self, record):
        if str(record.key) in self._keys:
            raise KeyError('Duplicate key')
        return super(ComponentMap, self).validate(record)


class SolutionMap(ReferenceMap):
    key_type = CoordinateEntry
    value_type = LocationEntry
