import json
from io import BytesIO

import cv2
import numpy as np
import requests
from PIL import Image
import os
import imghdr

from linnaeus.common import tryint
from linnaeus.models import ComponentMap, ReferenceMap, Component


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
        new_map = ReferenceMap()
        pixels = np.array(img)
        r = 0
        for row in cv2.cvtColor(pixels, cv2.COLOR_RGB2HSV_FULL):
            c = 0
            for col in row:
                new_map.add(c, r, *[np.asscalar(i) for i in col])
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
            new_map.add(*[tryint(i) for i in k.split('|')], *[tryint(i) for i in v])
        return new_map


class ComponentMapFactory:
    @classmethod
    def _build(cls, components):
        new_map = ComponentMap()
        for c in components:
            new_map.add(c.location, *c.dominant)
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
                components.append(Image.open(BytesIO(r.content)), url)
            except requests.ReadTimeout:
                continue
        return cls._build(components)

    @classmethod
    def from_portal(cls, query, **filters):
        """
        Creates a ComponentMap from images downloaded from an NHM Data Portal query. The
        images will be saved to a local folder.
        :param query: a search term
        :param filters: additional parameters
        :return: ComponentMap
        """
        return ComponentMap()

    @classmethod
    def deserialise(cls, txt):
        """
        Deserialise a JSON string to create a ReferenceMap.
        :param txt: JSON string
        :return: ReferenceMap
        """
        content = json.loads(txt)
        new_map = ComponentMap()
        for k, v in content.items():
            new_map.add(k, *[tryint(i) for i in v])
        return new_map