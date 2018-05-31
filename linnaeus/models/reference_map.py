from .map import BaseMap, BaseMapKey, MapRecord, MapValue


class CoordinateKey(BaseMapKey):
    def __init__(self, x, y):
        super(CoordinateKey, self).__init__(x * y)
        self.x = x
        self.y = y

    def __str__(self):
        return f'{self.x}|{self.y}'

    def validate(self):
        return isinstance(self.x, int) and isinstance(self.y, int) and self.key == (
                self.x * self.y)


class ReferenceMap(BaseMap):
    def validate(self, record):
        if str(record.key) in self._keys:
            raise KeyError('Duplicate key')
        if not isinstance(record.key, CoordinateKey) or not record.key.validate():
            raise KeyError
        if not record.value.validate():
            raise ValueError
        return True

    def add(self, x, y, h, s, v):
        record_key = CoordinateKey(x, y)
        record_value = MapValue(h, s, v)
        record = MapRecord(record_key, record_value)
        if self.validate(record):
            self._records.append(record)
            self._keys.add(str(record_key))
