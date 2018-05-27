import json
import math

import numpy as np
from progress.bar import IncrementalBar


def _load_from_file(path):
    with open(path, 'r') as f:
        return f.readlines()


def _tryint(i):
    try:
        if isinstance(i, np.generic):
            return np.asscalar(i)
        else:
            return int(i)
    except ValueError:
        return i


class MapRecord(object):
    def __init__(self, h, s, v, item):
        self.h = _tryint(h)
        self.s = _tryint(s)
        self.v = _tryint(v)
        self.item = item
        self.entry = (self.h, self.s, self.v)

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
        return self.entry.__hash__()

    def __str__(self):
        return f'{self.h}, {self.s}, {self.v}'

    def __sub__(self, other):
        h_diff = abs(self.h - other.h)
        s_diff = abs(self.s - other.s)
        v_diff = abs(self.v - other.v)
        return h_diff + s_diff + v_diff

    @property
    def csv(self):
        return ','.join([str(i) for i in [self.item, self.h, self.s, self.v]])

    @property
    def json(self):
        return self.item, self.entry


class PixelMapRecord(MapRecord):
    def __init__(self, h, s, v, x, y):
        super(PixelMapRecord, self).__init__(h, s, v, x * y)
        self.x = x
        self.y = y

    @property
    def csv(self):
        return ','.join([str(i) for i in [self.x, self.y, self.h, self.s, self.v]])

    @property
    def json(self):
        return '|'.join([str(self.x), str(self.y)]), self.entry


class Map(object):
    def __init__(self):
        self._records = []

    def __len__(self):
        return len(self._records)

    def add(self, r):
        self._records.append(r)

    @property
    def records(self):
        return sorted(self._records)

    def cost_matrix(self, other):
        # assumes self is the reference
        this_records = np.array(self.records)
        if len(self) > len(other):
            other_records = other.records * int(math.ceil(len(self) / len(other)))
        else:
            other_records = other.records
        other_records = np.array(other_records)
        print('Calculating mesh grids... ')
        xv, yv = np.meshgrid(other_records, this_records)
        print('Calculating score matrix (this may take a while)...')
        xy = (xv - yv) ** 2
        return xy.astype(int)

    def worker(self, i):
        return self.records[i - 1]

    def task(self, i, workers):
        try:
            return self.records[i - workers - 1]
        except IndexError:
            print(i, workers, len(self.records))
            raise IndexError

    def get_by_item(self, item):
        try:
            return next(r for r in self._records if r.item == item)
        except StopIteration:
            return None

    @classmethod
    def load_from_csv(cls, csv_, filepath=True):
        if filepath:
            csv_content = _load_from_file(csv_)
        else:
            csv_content = csv_.split('\n')
        rows = [r.strip().split(',') for r in csv_content]
        new_map = cls()
        bar = IncrementalBar(f'Loading {len(rows)} rows', max=len(rows),
                             suffix='%(percent)d%%, %(avg)d')
        for r in rows:
            if len(r) == 4:
                item = _tryint(r[0])
                h, s, v = [int(i) if i is not 'null' else None for i in r[1:]]
                new_map.add(MapRecord(h, s, v, item))
            elif len(r) == 5:
                x = _tryint(r[0])
                y = _tryint(r[1])
                h, s, v = [int(i) if i is not 'null' else None for i in r[2:]]
                new_map.add(PixelMapRecord(h, s, v, x, y))
            bar.next()
        bar.finish()
        return new_map

    @classmethod
    def load_from_json(cls, json_, filepath=True):
        if filepath:
            content = json.loads(_load_from_file(json_))
        else:
            content = json.loads(json_)
        new_map = cls()
        for k, hsv in content.items():
            h, s, v = [int(i) for i in hsv]
            if isinstance(k, str) and '|' in k:
                x, y = [_tryint(i) for i in k.split('|')]
                new_map.add(PixelMapRecord(h, s, v, x, y))
            else:
                item = _tryint(k)
                new_map.add(MapRecord(h, s, v, item))
        return new_map

    @property
    def csv(self):
        output = []
        for r in self.records:
            output.append(r.csv)
        return '\n'.join(output)

    @property
    def json(self):
        output = {}
        for r in self.records:
            k, v = r.json
            output[k] = v
        return json.dumps(output)

    def save(self, filename, mode='csv'):
        try:
            content = getattr(self, mode)
        except AttributeError:
            content = ''
        with open(filename, 'w') as f:
            f.write(content)
