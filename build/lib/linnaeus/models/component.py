import json
import os
import shutil
from collections import Counter

import numpy as np
from PIL import Image, ImageChops
from progress.bar import IncrementalBar

from linnaeus import utils
from linnaeus.config import constants
from .map import Map


class ComponentImage(object):
    def __init__(self, path=None, cache=None, base_url='{0}'):
        self.img = Image.open(path)
        self.id = path.split('/')[-1].split('.')[0]
        self.url = base_url.format(self.id)

        self.array = np.array(self.img)
        if cache is not None:
            self._dominant = cache[self.id]
        else:
            self._dominant = None
        self._dominant_nongrey = None

    def _get_dominant(self, f):
        hsv = utils.hsv_pixels(self.img)
        data = [tuple(p) for p in hsv if f(p)]
        if len(data) == 0:
            return None, None, None
        colours = Counter(data)
        return [int(i) for i in sorted(colours.items(), key=lambda x: x[1])[-1][0]]

    @property
    def dominant(self):
        if self._dominant is None:
            self._dominant = self._get_dominant(lambda x: True)
        return self._dominant

    @property
    def dominant_nongrey(self):
        if self._dominant_nongrey is None:
            self._dominant_nongrey = self._get_dominant(
                lambda x: x[1] > constants.saturation_threshold)
        return self._dominant_nongrey

    def adjust(self, h, s, v):
        """Adjusts the image to make the dominant colour the same as the target.

        :param h: the target hue (0 - 255)
        :param s: the target saturation (0 - 255)
        :param v: the target value (0 - 255)
        :return: the adjusted image as a PIL Image object
        """
        ch, cs, cv = self.dominant
        add_hsv = [0, 0, 0]
        subtract_hsv = [0, 0, 0]
        stats = [(h, ch), (s, cs),
                 (v, cv)]
        for i in range(len(stats)):
            target, current = stats[i]
            err = abs(target - current)
            if target > current:
                add_hsv[i] = err
            else:
                subtract_hsv[i] = err

        add_overlay = Image.new('HSV', self.img.size, color=tuple(add_hsv)).convert(
            'RGB')
        subtract_overlay = Image.new('HSV', self.img.size,
                                     color=tuple(subtract_hsv)).convert('RGB')
        img = ImageChops.add(self.img, add_overlay)
        img = ImageChops.subtract(img, subtract_overlay)
        return img

    @classmethod
    def load_components_from_folder(cls, path, cache, id_list=None):
        components = []
        file_list = os.listdir(path)
        if id_list is None:
            to_load = [f for f in file_list if
                       os.path.isfile(os.path.join(path, f))]
        else:
            to_load = [f for f in file_list if f.split('.')[0] in id_list]

        bar = IncrementalBar(f'Loading {len(to_load)} components', max=len(to_load),
                             suffix='%(percent)d%%, %(eta_td)s')
        for filename in to_load:
            try:
                ci = ComponentImage(path=os.path.join(path, filename), cache=cache)
                assert ci.img.size == constants.pixel_size
            except OSError:
                if not os.path.exists('failures'):
                    os.mkdir('failures')
                shutil.move(os.path.join(path, filename),
                            os.path.join('failures', filename))
                continue
            except Exception as e:
                continue
            if ci.img.mode != 'RGB':
                continue
            components.append(ci)
            bar.next()
        bar.finish()
        return components

    @classmethod
    def get_map(cls, components):
        component_map = Map()
        for c in components:
            component_map.add(*c.dominant, c.id)
        return component_map


class ComponentCache(object):
    def __init__(self, fn):
        self._fn = fn
        if os.path.exists(fn):
            with open(fn, 'r') as f:
                self._items = json.load(f)
        else:
            self._items = {}

    def __getitem__(self, item):
        return self._items.get(item, None)

    def cache(self, component: ComponentImage):
        self._items[component.id] = component.dominant

    def save(self):
        with open(self._fn, 'w') as f:
            self._items = json.dump(self._items, f)

    def fill(self, components):
        for component in components:
            self.cache(component)
        self.save()
