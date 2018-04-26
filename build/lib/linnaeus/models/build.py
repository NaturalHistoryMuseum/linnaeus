import math
import os
from datetime import datetime as dt

import numpy as np
from PIL import Image
from progress.bar import IncrementalBar
from scipy.optimize import linear_sum_assignment

from linnaeus.config import constants
from .component import ComponentCache, ComponentImage
from .map import Map
from .reference import ReferenceImage


class Builder(object):
    def __init__(self, ref: ReferenceImage, cache: ComponentCache):
        self.ref = ref
        self.canvas = None
        self.cache = cache

    def new_composite(self):
        self.canvas = Canvas(self.ref.size)

    def save_composite(self, fn):
        self.canvas.save(fn)

    def make_maps(self, component_path, save_dir=None):
        ref_map = self.ref.get_map()
        components = ComponentImage.load_components_from_folder(path=component_path,
                                                                cache=self.cache)
        comp_map = ComponentImage.get_map(components)
        if save_dir is not None:
            if not os.path.exists(save_dir):
                os.mkdir(save_dir)
            ref_map.save_to_csv(os.path.join(save_dir, 'ref.csv'))
            comp_map.save_to_csv(os.path.join(save_dir, 'comp.csv'))
        return ref_map, comp_map

    def load_maps(self, save_dir, component_path='.'):
        ref_path = os.path.join(save_dir, 'ref.csv')
        comp_path = os.path.join(save_dir, 'comp.csv')
        if os.path.exists(ref_path) and os.path.exists(comp_path):
            ref_map = Map.load_from_csv(ref_path)
            comp_map = Map.load_from_csv(comp_path)
        else:
            ref_map, comp_map = self.make_maps(component_path, save_dir)
        return ref_map, comp_map

    def fill(self, ref_map, comp_map, component_path):
        start = dt.now()
        cost_matrix = ref_map.cost_matrix(comp_map)
        print('Calculating assignments (this may also take a while)...')
        ref_pixel_ix, component_ix = linear_sum_assignment(cost_matrix)

        print('Finding the right records...')
        rr = ref_map.records
        cr = comp_map.records
        ref_pixels = [rr[i] for i in ref_pixel_ix]
        component_ids = [cr[i].item for i in component_ix]
        components = {ci.id: ci for ci in
                      ComponentImage.load_components_from_folder(component_path,
                                                                 self.cache,
                                                                 component_ids)}
        del rr, cr

        bar = IncrementalBar('Inserting images', maxlen=len(ref_pixels), suffix='%(percent)d%%, %(eta_td)s')
        for ref_pixel, comp_id in zip(ref_pixels, component_ids):
            ci = components[comp_id]
            self.canvas.paste(*self.canvas.get_row_col(ref_pixel.item),
                              ci.img, ci.id)
            bar.next()
        bar.finish()
        print(f'Time taken to fill canvas: {dt.now() - start}')


class Canvas(object):
    def __init__(self, size):
        self.ref_size = size
        self.w, self.h = size
        self.w *= constants.pixel_width
        self.h *= constants.pixel_height
        self.composite, self.component_id_array = Image.new('RGB', (self.w, self.h),
                                                            0), np.chararray(size)

    def get_row_col(self, index):
        w, h = self.ref_size
        row = int(math.floor(index / w))
        col = index - (w * row)
        return row, col

    def paste(self, row, col, image, component_id):
        x_offset = col * constants.pixel_width
        y_offset = row * constants.pixel_height
        self.composite.paste(image, (x_offset, y_offset))
        self.component_id_array[col, row] = component_id

    def save(self, fn):
        self.composite.save(fn)
