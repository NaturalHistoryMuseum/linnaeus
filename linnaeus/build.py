import math
import os
import pickle
from datetime import datetime as dt

import numpy as np
from PIL import Image
from ortools.graph import pywrapgraph
from progress.bar import IncrementalBar

from .component import ComponentCache, ComponentImage
from .config import constants
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
        for c in components:
            self.cache.cache(c)
        self.cache.save()
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

    @classmethod
    def load_solution(cls, path):
        with open(path, 'rb') as f:
            solution = pickle.load(f)
        return solution

    @classmethod
    def solve(cls, ref_map, comp_map, save_as=None):
        cost_matrix = ref_map.cost_matrix(comp_map)
        rows, cols = cost_matrix.shape
        print('Calculating assignments (this may also take a while)...')
        solver = pywrapgraph.SimpleMinCostFlow()
        pixel_nodes = [i + 1 for i in range(rows)]
        comp_nodes = [i + 1 for i in range(rows, rows + cols)]
        start_nodes = ([0] * rows) + [x for i in pixel_nodes for x in
                                      [i] * cols] + comp_nodes
        end_nodes = pixel_nodes + [x for i in range(rows) for x in comp_nodes] + (
                [rows + cols + 1] * cols)
        capacities = [1] * len(start_nodes)
        costs = ([0] * rows) + cost_matrix.flatten().tolist() + ([0] * cols)
        supplies = [rows] + ([0] * (rows + cols)) + [-rows]
        print(len(start_nodes))
        c = 0
        for i in range(len(start_nodes)):
            solver.AddArcWithCapacityAndUnitCost(start_nodes[i], end_nodes[i],
                                                 capacities[i], costs[i])
            c += 1
            print(c, end='\r')
        for i in range(len(supplies)):
            solver.SetNodeSupply(i, supplies[i])
        print('Solving...')
        if solver.Solve() == solver.OPTIMAL:
            print('Total cost = ', solver.OptimalCost())
            zipped = []
            c = 0
            print(solver.NumArcs())
            for arc in range(solver.NumArcs()):
                if 0 < solver.Tail(arc) <= len(ref_map) and solver.Head(arc) != len(
                        start_nodes):
                    if solver.Flow(arc) > 0:
                        pixel = ref_map.worker(solver.Tail(arc))
                        comp = comp_map.task(solver.Head(arc),
                                             len(ref_map))
                        zipped.append((pixel.item, comp.item, pixel.entry))
                c += 1
                print(c, end='\r')
            if save_as is not None:
                with open(save_as, 'wb') as f:
                    pickle.dump(zipped, f)
            return zipped

    def fill(self, ref_map, comp_map, component_path, maps_dir=None):
        start = dt.now()
        solution_file = os.path.join(maps_dir,
                                     'solution.pkl') if maps_dir is not None else None
        if solution_file is not None and os.path.exists(solution_file):
            print('Loading solution from file.')
            solution = Builder.load_solution(solution_file)
        else:
            solution = Builder.solve(ref_map, comp_map, save_as=solution_file)
        if solution is not None:
            components = {ci.id: ci for ci in
                          ComponentImage.load_components_from_folder(component_path,
                                                                     self.cache,
                                                                     [x[1] for x in
                                                                      solution])}
            bar = IncrementalBar('Inserting images', max=len(ref_map),
                                 suffix='%(percent)d%%, %(elapsed_td)s')
            for ref_pixel, comp_id, hsv in solution:
                ci = components[comp_id]
                self.canvas.paste(*self.canvas.get_row_col(ref_pixel),
                                  ci.adjust(*hsv), ci.id)
                bar.next()
            bar.finish()
            print(f'Time taken to fill canvas: {dt.now() - start}')
        else:
            print('No solution found.')


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
