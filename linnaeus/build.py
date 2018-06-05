import math

import numpy as np
from PIL import Image
from ortools.graph import pywrapgraph

from .config import constants
from .models.component import Component
from .models.maps import SolutionMap


class Builder(object):
    @classmethod
    def cost_matrix(cls, ref_map, comp_map):
        ref_records = np.array(ref_map.records)
        if len(ref_map) > len(comp_map):
            comp_records = comp_map.records * int(
                math.ceil(len(ref_map) / len(comp_map)))
        else:
            comp_records = comp_map.records
        comp_records = np.array(comp_records)
        xv, yv = np.meshgrid(comp_records, ref_records)
        xy = (xv - yv) ** 2
        return xy.astype(int)

    @classmethod
    def solve(cls, ref_map, comp_map, save_as=None):
        cost_matrix = cls.cost_matrix(ref_map, comp_map)
        rows, cols = cost_matrix.shape
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
        for i in range(len(start_nodes)):
            solver.AddArcWithCapacityAndUnitCost(start_nodes[i], end_nodes[i],
                                                 capacities[i], costs[i])
        for i in range(len(supplies)):
            solver.SetNodeSupply(i, supplies[i])
        if solver.Solve() == solver.OPTIMAL:
            solution = SolutionMap()
            for arc in range(solver.NumArcs()):
                if 0 < solver.Tail(arc) <= len(ref_map) and solver.Head(arc) != len(
                        start_nodes):
                    if solver.Flow(arc) > 0:
                        pixel = ref_map.worker(solver.Tail(arc))
                        comp = comp_map.task(solver.Head(arc),
                                             len(ref_map))
                        comp.key.target = pixel.value.entry
                        solution.add(pixel.key, comp.key)
            if save_as is not None:
                with open(save_as, 'w') as f:
                    f.write(solution.serialise())
            return solution

    @classmethod
    def fill(self, solution_map: SolutionMap, adjust=True):
        canvas = Canvas(solution_map.bounds())

        for record in solution_map.records:
            component = Component(record.value.entry)
            img = component.adjust(
                *record.value.target) if adjust and record.value.target is not None \
                else component.img
            canvas.paste(*record.key.entry, img, record.key.entry)
        return canvas


class Canvas(object):
    def __init__(self, size):
        self.ref_size = size
        self.w, self.h = size
        self.w *= constants.pixel_width
        self.h *= constants.pixel_height
        self.composite, self.component_id_array = Image.new('RGB', (self.w, self.h),
                                                            0), np.chararray(size)

    def paste(self, row, col, image, component_id):
        x_offset = col * constants.pixel_width
        y_offset = row * constants.pixel_height
        self.composite.paste(image, (x_offset, y_offset))
        self.component_id_array[col, row] = component_id

    def save(self, fn):
        self.composite.save(fn)
