import abc
import numpy as np
import json

from .entries import BaseEntry, CombinedEntry, CoordinateEntry, HsvEntry, LocationEntry


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

    def __sub__(self, other):
        if isinstance(self.value, HsvEntry) and isinstance(other.value, HsvEntry):
            return self.value - other.value
        else:
            raise NotImplementedError


class BaseMap(abc.ABC):
    key_type = BaseEntry
    value_type = HsvEntry

    def __init__(self):
        self._records = []
        self._keys = set()
        self._cache = True
        self._lock = True
        self._sortedrecords = None

    def __len__(self):
        return len(self._records)

    def __enter__(self):
        self._cache = False
        self._lock = False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._cache = True
        self._lock = True

    @property
    def records(self):
        # cached to avoid repeating expensive sorts
        if self._sortedrecords is None:
            sorted_records = sorted(self._records)
            if self._cache:
                self._sortedrecords = sorted_records
            else:
                return sorted_records
        return self._sortedrecords

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
        if self._lock:
            raise IOError('Locked.')
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
        return [i + 1 for i in
                max(self._records, key=lambda x: (x.key.x, x.key.y)).key.entry]


class ComponentMap(BaseMap):
    key_type = LocationEntry
    value_type = HsvEntry

    def validate(self, record):
        if str(record.key) in self._keys:
            raise KeyError('Duplicate key')
        return super(ComponentMap, self).validate(record)

    def reduce(self, target):
        self._sortedrecords = None
        self._records = np.random.choice(self._records, target, replace=False).tolist()
        self._keys = [str(r.key) for r in self._records]


class SolutionMap(ReferenceMap):
    key_type = CoordinateEntry
    value_type = CombinedEntry
    combined_types = {
        'path': LocationEntry,
        'target': HsvEntry
    }

    def validate(self, record):
        for k, e in record.value.entries.items():
            entry_type = self.combined_types.get(k, None)
            if entry_type is None or not isinstance(e, entry_type):
                return False
        return super(SolutionMap, self).validate(record)