import abc
import os

from linnaeus.models.maps import BaseMap


class BaseMapFactory(abc.ABC):
    @classmethod
    @abc.abstractmethod
    def deserialise(cls, txt):
        """
        Deserialise a JSON string to create a Map.
        :param txt: JSON string
        :return: Map
        """
        pass

    @classmethod
    @abc.abstractmethod
    def defaultpath(cls, identifier):
        """
        Returns a path to save the map to.
        :param identifier: a unique identifier
        :return: str
        """
        return os.path.join('maps',
                            f'{identifier}_{cls.__name__}.json')

    @classmethod
    @abc.abstractmethod
    def combine(cls, basemap: BaseMap, newmap: BaseMap, **kwargs) -> BaseMap:
        if not isinstance(newmap, type(basemap)):
            raise TypeError(
                f'Cannot combine {type(basemap).__name__} and {type(newmap).__name__}.')
        return basemap
