import imghdr
import json
import os
from io import BytesIO

import cv2
import numpy as np
import requests
from PIL import Image

from linnaeus.common import tryint
from linnaeus.config import constants
from linnaeus.models import (Component, ComponentMap, CoordinateEntry, HsvEntry,
                             LocationEntry, ReferenceMap)
from linnaeus.utils import portal


class MapFactory:
    @classmethod
    def deserialise(cls, txt):
        """
        Deserialises a block of JSON-formatted text and returns a Map object. Guesses
        the type of Map to return based on the content of the JSON.
        :param txt: JSON-formatted text string
        :return: Map
        """
        content = json.loads(txt)
        first_key = list(content.keys())[0]
        if len(first_key.split('|')) == 1:
            return ComponentMapFactory.deserialise(txt)
        elif len(first_key.split('|')) == 2:
            return ReferenceMapFactory.deserialise(txt)
        else:
            raise ValueError

    @classmethod
    def reference(cls):
        return ReferenceMapFactory

    @classmethod
    def component(cls):
        return ComponentMapFactory


class ReferenceMapFactory:
    @classmethod
    def _build(cls, img):
        """
        Resize the image as necessary and build the map.
        :param img: a PIL image object to build the map from
        :return: ReferenceMap
        """
        max_side = max(img.size)
        if max_side > constants.max_ref_side:
            adjust = constants.max_ref_side / max_side
            w, h = img.size
            w = int(w * adjust)
            h = int(h * adjust)
            img = img.resize((w, h))
        new_map = ReferenceMap()
        pixels = np.array(img)
        r = 0
        for row in cv2.cvtColor(pixels, cv2.COLOR_RGB2HSV_FULL):
            c = 0
            for col in row:
                rk = CoordinateEntry(c, r)
                rv = HsvEntry(*[np.asscalar(i) for i in col])
                new_map.add(rk, rv)
                c += 1
            r += 1
        return new_map

    @classmethod
    def from_image_local(cls, filepath):
        """
        Creates a ReferenceMap from a locally saved image file.
        :param filepath: the path to the image file
        :return: ReferenceMap
        """
        img = Image.open(filepath)
        return cls._build(img)

    @classmethod
    def from_image_url(cls, url):
        """
        Creates a ReferenceMap from an image that can be downloaded from a URL.
        :param url: the URL of the image
        :return: ReferenceMap
        """
        try:
            r = requests.get(url, timeout=10)
            img = Image.open(BytesIO(r.content))
            return cls._build(img)
        except requests.ReadTimeout:
            raise requests.ReadTimeout('Failed to download reference image.')

    @classmethod
    def from_image_bytes(cls, bytestring):
        """
        Creates a ReferenceMap from an image in its raw bytes form.
        :param bytestring: the bytes of the image
        :return: ReferenceMap
        """
        img = Image.open(BytesIO(bytestring))
        return cls._build(img)

    @classmethod
    def deserialise(cls, txt):
        """
        Deserialise a JSON string to create a ReferenceMap.
        :param txt: JSON string
        :return: ReferenceMap
        """
        content = json.loads(txt)
        new_map = ReferenceMap()
        for k, v in content.items():
            rk = CoordinateEntry(*[tryint(i) for i in k.split('|')])
            rv = HsvEntry(*[tryint(i) for i in v])
            new_map.add(rk, rv)
        return new_map


class ComponentMapFactory:
    @classmethod
    def _build(cls, components):
        """
        Builds a map from a list of component objects.
        :param components: list of Component objects
        :return: ComponentMap
        """
        new_map = ComponentMap()
        for c in components:
            rk = LocationEntry(c.location)
            rv = HsvEntry(*c.dominant)
            new_map.add(rk, rv)
        return new_map

    @classmethod
    def from_local(cls, files=None, folders=None):
        """
        Creates a ComponentMap from local files.
        :param files: paths to specific files
        :param folders: paths to folders containing images to be included
        :return: ComponentMap
        """
        if folders is None:
            folders = []
        if files is None:
            files = []
        components = []
        for folder in folders:
            for dirpath, dirnames, filenames in os.walk(folder):
                paths = [os.path.join(dirpath, f) for f in filenames]
                files += [p for p in paths if imghdr.what(p) is not None]
        for f in files:
            try:
                components.append(Component(Image.open(f), f))
            except IOError:
                continue
        return cls._build(components)

    @classmethod
    def from_urls(cls, urls):
        """
        Creates a ComponentMap from images downloaded from URLs.
        :param urls: URLs of images
        :return: ComponentMap
        """
        components = []
        for url in urls:
            try:
                r = requests.get(url, timeout=10)
                components.append(Component(Image.open(BytesIO(r.content)), url))
            except requests.ReadTimeout:
                continue
        return cls._build(components)

    @classmethod
    def from_portal(cls, query, **filters):
        """
        Creates a ComponentMap from images downloaded from an NHM Data Portal query.
        :param query: a search term
        :param filters: additional parameters
        :return: ComponentMap
        """
        components = []
        for page in portal.API.assets(portal.API.COLLECTIONS, query=query, **filters):
            for asset in page:
                try:
                    r = requests.get(
                        asset.get('identifier').replace('preview', 'thumbnail'),
                        timeout=2)
                    components.append(Component(Image.open(BytesIO(r.content)),
                                                asset.get('identifier')))
                except requests.ReadTimeout:
                    continue
        return cls._build(components)

    @classmethod
    def deserialise(cls, txt):
        """
        Deserialise a JSON string to create a ComponentMap.
        :param txt: JSON string
        :return: ComponentMap
        """
        content = json.loads(txt)
        new_map = ComponentMap()
        for k, v in content.items():
            rk = LocationEntry(k)
            rv = HsvEntry(*[tryint(i) for i in v])
            new_map.add(rk, rv)
        return new_map
