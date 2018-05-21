import math

import numpy as np
from progress.bar import IncrementalBar


class MapRecord(object):
    def __init__(self, h, s, v, item):
        self.h = h
        self.s = s
        self.v = v
        self.item = item
        self.entry = (h, s, v)

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


class Map(object):
    def __init__(self):
        self._records = []

    def __len__(self):
        return len(self._records)

    def add(self, h, s, v, item):
        r = MapRecord(h, s, v, item)
        self._records.append(r)

    @classmethod
    def load_from_csv(cls, csv_file):
        with open(csv_file, 'r') as f:
            rows = [r.strip().split(',') for r in f.readlines()]
        new_map = cls()
        bar = IncrementalBar(f'Loading {len(rows)} rows', max=len(rows),
                             suffix='%(percent)d%%, %(avg)d')
        for r in rows:
            h, s, v = [int(i) if i is not 'null' else None for i in r[:3]]
            try:
                item = int(r[3])
            except ValueError:
                item = r[3]
            new_map.add(h, s, v, item)
            bar.next()
        bar.finish()
        return new_map

    def save_to_csv(self, csv_file):
        bar = IncrementalBar(f'Saving {len(self)} rows', max=len(self),
                             suffix='%(percent)d%%')
        with open(csv_file, 'w') as f:
            for r in self.records:
                f.write(','.join([str(r), str(r.item)]))
                f.write('\n')
                bar.next()
        bar.finish()

    @property
    def csv(self):
        output = []
        for r in self.records:
            output.append(','.join([str(r), str(r.item)]))
        return '\n'.join(output)

    def save(self, filename, mode='csv'):
        try:
            content = getattr(self, mode)
        except AttributeError:
            content = ''
        with open(filename, 'w') as f:
            f.write(content)

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
