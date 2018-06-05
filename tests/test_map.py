from datetime import datetime as dt

import nose.tools as nosetools

from linnaeus.models import (ComponentMap, CoordinateEntry, HsvEntry, LocationEntry,
                             MapRecord, ReferenceMap)


class TestMapValue:
    def setUp(self):
        self.black = HsvEntry(0, 0, 0)
        self.white = HsvEntry(0, 0, 255)

    def test_comparisons(self):
        nosetools.assert_greater(self.white, self.black)
        nosetools.assert_greater_equal(self.white, self.black)
        nosetools.assert_greater_equal(self.white, self.white)
        nosetools.assert_equal(self.black, self.black)
        nosetools.assert_less(self.black, self.white)
        nosetools.assert_less_equal(self.black, self.white)
        nosetools.assert_less_equal(self.black, self.black)

    def test_serialise(self):
        nosetools.assert_equal(str(self.black), '0,0,0')
        nosetools.assert_equal(str(self.white), '0,0,255')

    def test_hash(self):
        nosetools.assert_equal(hash(self.black), 1267304713960822739)
        nosetools.assert_equal(hash(self.white), 1267304713903735338)

    def test_subtract(self):
        nosetools.assert_equal(self.white - self.black, self.black - self.white)
        nosetools.assert_equal(self.white - self.black, 255)


class TestCoordinateEntry:
    def setUp(self):
        self.key = CoordinateEntry(0, 0)
        self.bad_key = CoordinateEntry(1.2, 3.4)

    def test_validate(self):
        nosetools.assert_true(self.key.validate())
        nosetools.assert_false(self.bad_key.validate())


class TestMapRecord:
    def setUp(self):
        self.black = MapRecord(CoordinateEntry(0, 0), HsvEntry(0, 0, 0))
        self.white = MapRecord(CoordinateEntry(1, 1), HsvEntry(0, 0, 255))

    def test_comparisons(self):
        nosetools.assert_greater(self.white, self.black)
        nosetools.assert_greater_equal(self.white, self.black)
        nosetools.assert_greater_equal(self.white, self.white)
        nosetools.assert_equal(self.black, self.black)
        nosetools.assert_less(self.black, self.white)
        nosetools.assert_less_equal(self.black, self.white)
        nosetools.assert_less_equal(self.black, self.black)


class TestComponentMap:
    def setUp(self):
        self.map = ComponentMap()

    def _add_records(self):
        keys = [LocationEntry(i) for i in 'abcd']
        values = [HsvEntry(*i) for i in [(0, 0, 0), (1, 1, 1), (2, 2, 2), (0, 2, 1)]]
        for k, v in zip(keys, values):
            self.map.add(k, v)
        self.serialised = '{"a": [0, 0, 0], "b": [1, 1, 1], "c": [2, 2, 2], ' \
                          '"d": [0, 2, 1]}'

    def test_add_records(self):
        self.map.add(LocationEntry('random key'), HsvEntry(0, 0, 0))
        with nosetools.assert_raises(ValueError):
            self.map.add(LocationEntry('values too high'), HsvEntry(3000, 3000, 3000))
        with nosetools.assert_raises(ValueError):
            self.map.add(LocationEntry('negative values'), HsvEntry(-1, -2, -3))
        with nosetools.assert_raises(KeyError):
            self.map.add(LocationEntry('random key'), HsvEntry(1, 1, 1))
        with nosetools.assert_raises(TypeError):
            self.map.add(LocationEntry(0), HsvEntry(0, 0, 0))

    def test_add_many_records(self):
        start = dt.now()
        for i in range(100000):
            self.map.add(LocationEntry(str(i)), HsvEntry(0, 0, 0))
        elapsed = (dt.now() - start).total_seconds()
        nosetools.assert_less(elapsed, 10)

    def test_sort_records(self):
        self._add_records()
        nosetools.assert_is_not_none(self.map.records)
        nosetools.assert_equal(str(self.map.records[-1].key), 'c')

    def test_serialise(self):
        self._add_records()
        s = self.map.serialise()
        nosetools.assert_equal(s, self.serialised)


class TestReferenceMap(TestComponentMap):
    def setUp(self):
        self.map = ReferenceMap()

    def _add_records(self):
        self.map.add(CoordinateEntry(0, 0), HsvEntry(0, 0, 0))
        self.map.add(CoordinateEntry(1, 1), HsvEntry(1, 1, 1))
        self.map.add(CoordinateEntry(0, 1), HsvEntry(2, 2, 2))
        self.map.add(CoordinateEntry(2, 2), HsvEntry(0, 2, 1))
        self.serialised = '{"0|0": [0, 0, 0], "1|1": [1, 1, 1], "0|1": [2, 2, 2], ' \
                          '"2|2": [0, 2, 1]}'

    def test_add_records(self):
        self.map.add(CoordinateEntry(0, 0), HsvEntry(0, 0, 0))
        with nosetools.assert_raises(ValueError):
            self.map.add(CoordinateEntry(1, 1), HsvEntry(3000, 3000, 3000))
        with nosetools.assert_raises(ValueError):
            self.map.add(CoordinateEntry(2, 2), HsvEntry(-1, -2, -3))
        with nosetools.assert_raises(KeyError):
            self.map.add(CoordinateEntry(0, 0), HsvEntry(1, 1, 1))
        with nosetools.assert_raises(KeyError):
            self.map.add(CoordinateEntry(1.2, 3), HsvEntry(0, 0, 0))

    def test_add_many_records(self):
        start = dt.now()
        for i in range(100000):
            self.map.add(CoordinateEntry(i, i), HsvEntry(0, 0, 0))
        elapsed = (dt.now() - start).total_seconds()
        nosetools.assert_less(elapsed, 10)

    def test_sort_records(self):
        self._add_records()
        nosetools.assert_is_not_none(self.map.records)
        nosetools.assert_equal(str(self.map.records[-1].key), '0|1')
