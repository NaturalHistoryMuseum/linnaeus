import itertools
from io import BytesIO

import numpy as np
import pandas as pd
from PIL import Image

from linnaeus import utils
from linnaeus.config import constants
from .map import Map


class ReferenceImage(object):
    def __init__(self, path=None, data=None):
        if path is not None:
            self.img = Image.open(path)
        elif data is not None:
            self.img = Image.open(BytesIO(data))
        self._resize()
        self.pixels = self._group_pixels()

    def _resize(self):
        max_side = max(self.img.size)
        if max_side > constants.max_ref_side:
            adjust = constants.max_ref_side / max_side
            w, h = self.img.size
            w = int(w * adjust)
            h = int(h * adjust)
            self.img = self.img.resize((w, h))

    @property
    def size(self):
        return self.img.size

    def _group_pixels(self):
        hsv = utils.hsv_pixels(self.img)
        hsv = [[int(x) for x in hsv[i]] + [i] for i in range(len(hsv))]
        group_by_hue = {k: [i[1:] for i in v] for k, v in
                        itertools.groupby(sorted(hsv, key=lambda x: x[0]),
                                          key=lambda x: x[0])}
        group_by_saturation = {hue: {k: [i[1:] for i in v] for k, v in
                                     itertools.groupby(sorted(sv, key=lambda x: x[0]),
                                                       key=lambda x: x[0])} for hue, sv
                               in group_by_hue.items()}
        group_by_value = {}
        for hue, sats in group_by_saturation.items():
            group_by_value[hue] = {}
            for sat, vals in sats.items():
                val_dict = {k: [i[-1] for i in v] for k, v in
                            itertools.groupby(sorted(vals, key=lambda x: x[0]),
                                              key=lambda x: x[0])}
                group_by_value[hue][sat] = val_dict
        return group_by_value

    def get_map(self):
        ref_map = Map()
        hsv_pixels = utils.hsv_pixels(self.img)
        hsv_to_index = [[int(x) for x in hsv_pixels[i]] + [i] for i in
                        range(len(hsv_pixels))]
        for p in hsv_to_index:
            ref_map.add(*p)
        return ref_map

    def save_as_csv(self, fn):
        hsv = pd.DataFrame(utils.hsv_pixels(self.img), columns=['h', 's', 'v'])
        hsv.to_csv(fn)

    def show(self):
        utils.show(np.array(self.img))
