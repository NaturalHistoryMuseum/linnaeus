import math

import cv2
import imghdr
import json
import numpy as np
import os
import requests
from PIL import Image
from io import BytesIO

from linnaeus.common import tryint
from linnaeus.config import constants
from linnaeus.models import (CombinedEntry, Component, ComponentMap, CoordinateEntry,
                             HsvEntry, LocationEntry, ReferenceMap, SolutionMap)
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

    @classmethod
    def solution(cls):
        return SolutionMapFactory

    @classmethod
    def load_text(cls, filepath):
        """
        Convenience method for loading content.
        :param filepath: the path to the file
        :return: str
        """
        with open(filepath, 'r') as f:
            return f.read()

    @classmethod
    def save_text(cls, filepath, txt):
        """
        Convenience method for saving content to a file.
        :param filepath: the path to the file
        """
        with open(filepath, 'w') as f:
            f.write(txt)


class ReferenceMapFactory:
    @classmethod
    def _build(cls, img):
        """
        Resize the image as necessary and build the map.
        :param img: a PIL image object to build the map from
        :return: ReferenceMap
        """
        w, h = img.size
        current_size = w * h
        if current_size > constants.max_ref_size:
            adjust = math.sqrt(constants.max_ref_size / current_size)
            nw = int(w * adjust)
            nh = int(h * adjust)
            img = img.resize((nw, nh))
        pixels = np.array(img)
        rn = pixels.shape[0]
        cn = pixels.shape[1]
        rows = np.repeat(np.arange(rn), cn).reshape(rn, cn, 1)
        cols = np.tile(np.arange(cn), rn).reshape(rn, cn, 1)
        hsv_pixels = cv2.cvtColor(pixels, cv2.COLOR_RGB2HSV_FULL)
        hsv_pixels = np.c_[rows, cols, hsv_pixels]
        with ReferenceMap() as new_map:
            if img.mode == 'RGBA':
                transparent_mask = pixels[..., 3] > 0
                hsv_pixels = hsv_pixels[transparent_mask]
            else:
                hsv_pixels = np.concatenate(hsv_pixels)
            for pixel in hsv_pixels:
                rk = CoordinateEntry(np.asscalar(pixel[1]), np.asscalar(pixel[0]))
                rv = HsvEntry(*[np.asscalar(i) for i in pixel[2:]])
                new_map.add(rk, rv)
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
        with ReferenceMap() as new_map:
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
        with ComponentMap() as new_map:
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
        # TODO: use a github-hosted cache
        for page in portal.API.assets(portal.API.COLLECTIONS, query=query, **filters):
            for asset in page:
                try:
                    r = requests.get(
                        asset.get('identifier').replace('preview', 'thumbnail'),
                        timeout=10)
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
        with ComponentMap() as new_map:
            for k, v in content.items():
                rk = LocationEntry(k)
                rv = HsvEntry(*[tryint(i) for i in v])
                new_map.add(rk, rv)
            return new_map


class SolutionMapFactory:
    @classmethod
    def deserialise(cls, txt):
        """
        Deserialise a JSON string to create a SolutionMap.
        :param txt: JSON string
        :return: SolutionMap
        """
        content = json.loads(txt)
        with SolutionMap() as new_map:
            for k, v in content.items():
                rk = CoordinateEntry(*[tryint(i) for i in k.split('|')])
                rv = CombinedEntry(**{
                    ek: SolutionMap.combined_types[ek](*ev) if isinstance(ev, list) else
                    SolutionMap.combined_types[ek](ev) for ek, ev in v.items()})
                new_map.add(rk, rv)
            return new_map
