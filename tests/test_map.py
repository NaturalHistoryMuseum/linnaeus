from datetime import datetime as dt

import nose.tools as nosetools

from linnaeus.models import ComponentMap, CoordinateKey, MapRecord, MapValue, ReferenceMap


class TestMapValue:
    def setUp(self):
        self.black = MapValue(0, 0, 0)
        self.white = MapValue(0, 0, 255)

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


class TestCoordinateKey:
    def setUp(self):
        self.key = CoordinateKey(0, 0)
        self.bad_key = CoordinateKey(1.2, 3.4)

    def test_validate(self):
        nosetools.assert_true(self.key.validate())
        nosetools.assert_false(self.bad_key.validate())


class TestMapRecord:
    def setUp(self):
        self.black = MapRecord(CoordinateKey(0, 0), MapValue(0, 0, 0))
        self.white = MapRecord(CoordinateKey(1, 1), MapValue(0, 0, 255))

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
        self.map.add('ab', 0, 0, 0)
        self.map.add('ef', 1, 1, 1)
        self.map.add('cd', 2, 2, 2)
        self.map.add('gh', 0, 2, 1)
        self.serialised = '{"ab": [0, 0, 0], "ef": [1, 1, 1], "cd": [2, 2, 2], ' \
                          '"gh": [0, 2, 1]}'

    def test_add_records(self):
        self.map.add('random key', 0, 0, 0)
        with nosetools.assert_raises(ValueError):
            self.map.add('values too high', 3000, 3000, 3000)
        with nosetools.assert_raises(ValueError):
            self.map.add('negative values', -1, -2, -3)
        with nosetools.assert_raises(KeyError):
            self.map.add('random key', 1, 1, 1)
        with nosetools.assert_raises(KeyError):
            self.map.add(0, 0, 0, 0)

    def test_add_many_records(self):
        start = dt.now()
        for i in range(100000):
            self.map.add(str(i), 0, 0, 0)
        elapsed = (dt.now() - start).total_seconds()
        nosetools.assert_less(elapsed, 10)

    def test_sort_records(self):
        self._add_records()
        nosetools.assert_is_not_none(self.map.records)
        nosetools.assert_equal(self.map.records[-1].key.key, 'cd')

    def test_serialise(self):
        self._add_records()
        s = self.map.serialise()
        nosetools.assert_equal(s, self.serialised)


class TestReferenceMap(TestComponentMap):
    def setUp(self):
        self.map = ReferenceMap()

    def _add_records(self):
        self.map.add(0, 0, 0, 0, 0)
        self.map.add(1, 1, 1, 1, 1)
        self.map.add(0, 1, 2, 2, 2)
        self.map.add(2, 2, 0, 2, 1)
        self.serialised = '{"0|0": [0, 0, 0], "1|1": [1, 1, 1], "0|1": [2, 2, 2], ' \
                          '"2|2": [0, 2, 1]}'

    def test_add_records(self):
        self.map.add(0, 0, 0, 0, 0)
        with nosetools.assert_raises(ValueError):
            self.map.add(1, 1, 3000, 3000, 3000)
        with nosetools.assert_raises(ValueError):
            self.map.add(2, 2, -1, -2, -3)
        with nosetools.assert_raises(KeyError):
            self.map.add(0, 0, 1, 1, 1)
        with nosetools.assert_raises(KeyError):
            self.map.add(1.2, 3, 0, 0, 0)

    def test_add_many_records(self):
        start = dt.now()
        for i in range(100000):
            self.map.add(i, i, 0, 0, 0)
        elapsed = (dt.now() - start).total_seconds()
        nosetools.assert_less(elapsed, 10)

    def test_sort_records(self):
        self._add_records()
        nosetools.assert_is_not_none(self.map.records)
        nosetools.assert_equal(str(self.map.records[-1].key), '0|1')

