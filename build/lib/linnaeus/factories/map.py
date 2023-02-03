import cv2
import filetype
import json
import numpy as np
import os
import qrcode
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

from linnaeus.common import tryint
from linnaeus.config import ProgressLogger, constants
from linnaeus.models import (Component, ComponentMap, CoordinateEntry,
                             HsvEntry, LocationEntry, ReferenceMap, SolutionMap)
from linnaeus.utils import portal
from ._base import BaseMapFactory


class SolutionMapFactory(BaseMapFactory):
    product_class = SolutionMap

    @classmethod
    def combine(cls, basemap, newmap, position='C', offset=(0,0), overlay=True):
        """
        Combine reference maps.
        :param basemap: the first Map
        :param newmap: the new Map to add to the first
        :param position: for calculating the position; e.g. C (center), N (north),
                        or a tuple of coordinates to manually specify the position from
                        top left
        :param offset: offset from the position
        :param overlay: True to add the new ref on top of the base, False to add
                        it next to the base image with no overlap (ignored if gravity is
                        C or tuple)
        :return: Map
        """
        super(SolutionMapFactory, cls).combine(basemap, newmap)
        base_w, base_h, new_w, new_h = basemap.bounds + newmap.bounds
        if isinstance(position, tuple):
            x, y = position
        else:
            gravity = position.upper()
            # find centerpoints
            horizontal = 'C'
            vertical = 'C'
            lookup_h = {
                'C': (base_w - new_w) // 2,
                'E': base_w - new_w if overlay else base_w,
                'W': 0 if overlay else -new_w
                }
            lookup_v = {
                'C': (base_h - new_h) // 2,
                'N': 0 if overlay else -new_h,
                'S': base_h - new_h if overlay else base_h
                }
            try:
                horizontal = next(i for i in gravity if i in lookup_h.keys())
            except StopIteration:
                pass
            try:
                vertical = next(i for i in gravity if i in lookup_v.keys())
            except StopIteration:
                pass
            x = lookup_h[horizontal]
            y = lookup_v[vertical]
        x += offset[0]
        y += offset[1]
        w = max(new_w + x, base_w) - min(x, 0)
        h = max(new_h + y, base_h) - min(y, 0)
        with cls.product_class() as combined_map, ProgressLogger(
                len(basemap) + len(newmap), 10) as p:
            def add_to_map(ox, oy, itermap):
                for r in itermap.records:
                    rx, ry = r.key.entry
                    rk = CoordinateEntry(rx + ox, ry + oy)
                    combined_map[rk] = r.value
                    p.next()

            add_to_map(abs(min(x, 0)), abs(min(y, 0)), basemap)
            add_to_map(max(x, 0), max(y, 0), newmap)
            return combined_map

    @classmethod
    def defaultpath(cls, identifier):
        return os.path.join('maps',
                            f'{identifier}_solution_{str(constants.size)}_'
                            f'{constants.max_components}.json')

    @classmethod
    def deserialise(cls, txt):
        content = json.loads(txt)
        with cls.product_class() as new_map, ProgressLogger(len(content), 10) as p:
            for k, v in content.items():
                rk = cls._deserialisekey(k)
                rv = cls._deserialisevalue(v)
                new_map.add(rk, rv)
                p.next()
            return new_map

    @classmethod
    def _deserialisekey(cls, k):
        return cls.product_class.key_type(*[tryint(i) for i in k.split('|')])

    @classmethod
    def _deserialisevalue(cls, v):
        return cls.product_class.value_type(**{
            ek: cls.product_class.combined_types[ek](*ev) if isinstance(ev, list) else
            cls.product_class.combined_types[ek](ev) for ek, ev in v.items()})


class ReferenceMapFactory(SolutionMapFactory):
    product_class = ReferenceMap

    @classmethod
    def defaultpath(cls, identifier):
        return os.path.join('maps',
                            f'{identifier}_ref_{str(constants.size)}.json')

    @classmethod
    def _deserialisevalue(cls, v):
        return cls.product_class.value_type(*[tryint(i) for i in v])

    @classmethod
    def get_hsv_pixels(cls, pixels):
        """
        Get labelled (i.e. row number and column number appended) HSV pixels from an
        array of RGBA pixels.
        :param pixels: a numpy array of RGBA pixels
        :return: a numpy array of [row, col, h, s, v] entries
        """
        assert pixels.shape[-1] == 4
        rn = pixels.shape[0]
        cn = pixels.shape[1]
        rows = np.repeat(np.arange(rn), cn).reshape(rn, cn, 1)
        cols = np.tile(np.arange(cn), rn).reshape(rn, cn, 1)
        hsv_pixels = cv2.cvtColor(pixels, cv2.COLOR_RGB2HSV_FULL)
        hsv_pixels = np.c_[rows, cols, hsv_pixels]
        transparent_mask = pixels[..., 3] > 0
        hsv_pixels = hsv_pixels[transparent_mask]
        return hsv_pixels

    @classmethod
    def _build(cls, img, resize=True):
        """
        Resize the image as necessary and build the map.
        :param img: a PIL image object to build the map from
        :param resize: True to resize the image based on the config, False to ignore
        :return: ReferenceMap
        """
        if resize:
            w, h = img.size
            img = img.resize(constants.size.dimensions(w, h))
        img = img.convert(mode='RGBA')
        pixels = np.array(img)
        hsv_pixels = cls.get_hsv_pixels(pixels)
        with ReferenceMap() as new_map:
            with ProgressLogger(len(hsv_pixels), 10) as p:
                for pixel in hsv_pixels:
                    rk = CoordinateEntry(np.asscalar(pixel[1]), np.asscalar(pixel[0]))
                    rv = HsvEntry(*[np.asscalar(i) for i in pixel[2:]])
                    new_map.add(rk, rv)
                    p.next()
            return new_map

    @classmethod
    def from_image_local(cls, filepath, resize=True):
        """
        Creates a ReferenceMap from a locally saved image file.
        :param filepath: the path to the image file
        :return: ReferenceMap
        """
        img = Image.open(filepath)
        return cls._build(img, resize)

    @classmethod
    def from_image_url(cls, url, resize=True):
        """
        Creates a ReferenceMap from an image that can be downloaded from a URL.
        :param url: the URL of the image
        :return: ReferenceMap
        """
        try:
            r = requests.get(url, timeout=10)
            img = Image.open(BytesIO(r.content))
            return cls._build(img, resize)
        except requests.ReadTimeout:
            raise requests.ReadTimeout('Failed to download reference image.')

    @classmethod
    def from_image_bytes(cls, bytestring, resize=True):
        """
        Creates a ReferenceMap from an image in its raw bytes form.
        :param bytestring: the bytes of the image
        :return: ReferenceMap
        """
        img = Image.open(BytesIO(bytestring))
        return cls._build(img, resize)

    @classmethod
    def from_image_pil(cls, img, resize=True):
        """
        Creates a ReferenceMap from a PIL Image object.
        :param img: the image in PIL object form
        :return: ReferenceMap
        """
        return cls._build(img, resize)

    @classmethod
    def from_text(cls, text, font_file, font_size=20, font_colour=(0, 0, 0, 255)):
        """
        Creates a ReferenceMap from an image of text, rendered by PIL.
        :param text: the text to render
        :param font_file: the .ttf or .otf file for the font
        :param font_size: the size of the rendered text (in px)
        :param font_colour: the RGBA colour of the rendered text
        :return: ReferenceMap
        """
        font = ImageFont.truetype(font_file, font_size)
        # draw as binary (b/w) image to avoid antialiasing
        img = Image.new('1', font.getsize_multiline(text), 1)
        draw = ImageDraw.Draw(img)
        draw.multiline_text((0, 0), text, font=font, fill=0)
        pixels = np.array(img.convert('RGBA'))
        mask = pixels[..., 0] > 0
        pixels[..., 3][mask] = 0  # then convert white pixels to transparent
        pixels[~mask] = np.array(font_colour)
        pixels = pixels[pixels[..., 3].sum(axis=1) > 0]  # delete empty rows
        img = Image.fromarray(pixels, 'RGBA')
        return cls._build(img, resize=False)

    @classmethod
    def from_qr_data(cls, data, colour=(0, 0, 0, 255), size=1):
        """
        Makes a ReferenceMap from an image of a QR code, generated by qrcode and PIL.
        :param data: the data to generate the QR code from
        :param colour: the colour of the QR code blocks
        :param size: the size of each QR code block
        :return: ReferenceMap
        """
        qr = qrcode.QRCode(
            box_size=size,
            border=0
            )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color='black', back_color='transparent').get_image()
        pixels = np.array(img)
        colour = np.array(colour)
        pixels[pixels[..., 3] > 0] = colour
        return cls._build(Image.fromarray(pixels, 'RGBA'), resize=False)


class ComponentMapFactory(BaseMapFactory):
    product_class = ComponentMap

    @classmethod
    def combine(cls, basemap, newmap, prefix='.'):
        super(ComponentMapFactory, cls).combine(basemap, newmap)
        addtl_prefix = ''
        if not os.path.exists(os.path.join(prefix, basemap.records[0].key.path)):
            raise ValueError(
                f'{os.path.join(prefix, basemap.records[0].key.path)} does not exist.')
        elif not os.path.exists(os.path.join(prefix, newmap.records[0].key.path)):
            filename = os.path.split(newmap.records[0].key.path)[-1]
            for d, subdirs, files in os.walk(prefix):
                if filename in files:
                    addtl_prefix = d
                    break
        with basemap, ProgressLogger(len(newmap), 10) as p:
            for r in newmap.records:
                try:
                    rk = LocationEntry(os.path.join(addtl_prefix, r.key.path))
                    basemap.add(rk, r.value)
                except KeyError:
                    pass
                p.next()
        return basemap

    @classmethod
    def defaultpath(cls, identifier):
        return os.path.join('maps',
                            f'{identifier}_'
                            f'{constants.dominant_colour_method}.json')

    @classmethod
    def deserialise(cls, txt):
        content = json.loads(txt)
        with ComponentMap() as new_map, ProgressLogger(len(content), 10) as p:
            for k, v in content.items():
                rk = LocationEntry(k)
                rv = HsvEntry(*[tryint(i) for i in v])
                new_map.add(rk, rv)
                p.next()
            return new_map

    @classmethod
    def _build(cls, components):
        """
        Builds a map from a list of component objects.
        :param components: list of Component objects
        :return: ComponentMap
        """
        with ComponentMap() as new_map, ProgressLogger(len(components), 10) as p:
            for c in components:
                rk = LocationEntry(c.location)
                rv = HsvEntry(*c.dominant)
                new_map.add(rk, rv)
                p.next()
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
                files += [p for p in paths if filetype.is_image(p)]
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


class MapFactory(BaseMapFactory):
    """
    A controller factory, not a base. Identifies Map types and delegates to other
    MapFactory classes rather than doing any Map generation itself. Also provides
    generic helper methods, e.g. for loading and dumping text from/to file.
    """

    factories = {
        ReferenceMap: ReferenceMapFactory,
        ComponentMap: ComponentMapFactory,
        SolutionMap: SolutionMapFactory
        }

    @classmethod
    def combine(cls, basemap, newmap, **kwargs):
        return cls.factories[type(basemap)].combine(basemap, newmap, **kwargs)

    @classmethod
    def defaultpath(cls, identifier):
        super(MapFactory, cls).defaultpath(identifier)

    @classmethod
    def deserialise(cls, txt):
        """
        Deserialises a block of JSON-formatted text and returns a Map object. Guesses
        the type of Map to return based on the content of the JSON.
        :param txt: JSON-formatted text string
        :return: Map
        """
        return cls.identify(txt).deserialise(txt)

    @classmethod
    def identify(cls, txt):
        """
        Guesses the type of Map represented by the input JSON-formatted text
        string. Returns the relevant MapFactory.
        :param txt: JSON-formatted text string
        :return: MapFactory subtype
        """
        content = json.loads(txt)
        first_key = list(content.items())[0]
        if '|' in first_key[0] and len(first_key[0].split('|')) == 2:
            # either ref or solution
            if isinstance(first_key[1], dict):
                return cls.solution()
            else:
                return cls.reference()
        else:
            return cls.component()

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
