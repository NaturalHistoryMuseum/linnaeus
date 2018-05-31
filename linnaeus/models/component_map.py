from .map import BaseMap


class ComponentMap(BaseMap):
    def validate(self, record):
        if record.key.key in self._keys:
            raise KeyError('Duplicate key')
        if not record.value.validate():
            raise ValueError
        if self._keytype is not None:
            if not isinstance(record.key.key, self._keytype):
                raise KeyError(f'Key should be {self._keytype}')
        else:
            self._keytype = type(record.key.key)
        return True
