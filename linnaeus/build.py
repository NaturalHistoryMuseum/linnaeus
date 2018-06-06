import math
from datetime import datetime as dt, timedelta

import numpy as np
from PIL import Image
from ortools.graph import pywrapgraph

from .config import constants, logger
from .models import CombinedEntry, Component, SolutionMap


class Builder(object):
    @classmethod
    def cost_matrix(cls, ref_map, comp_map):
        ref_map.done()
        comp_map.done()
        logger.debug('calculating cost matrix')
        ref_records = np.array(ref_map.records)
        if len(ref_map) > len(comp_map):
            comp_records = comp_map.records * int(
                math.ceil(len(ref_map) / len(comp_map)))
        else:
            comp_records = comp_map.records
        comp_records = np.array(comp_records)
        xv, yv = np.meshgrid(comp_records, ref_records)
        xy = (xv - yv) ** 2
        logger.debug('finished calculating cost matrix')
        return xy.astype(int)

    @classmethod
    def solve(cls, ref_map, comp_map):
        ref_map.done()
        comp_map.done()
        cost_matrix = cls.cost_matrix(ref_map, comp_map)
        rows, cols = cost_matrix.shape
        logger.debug('constructing solver')
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
        logger.debug('solving')
        if solver.Solve() == solver.OPTIMAL:
            solution = SolutionMap()
            logger.debug('building solution map')
            start = dt.now()
            logger.debug(f'processing {solver.NumArcs()} arcs')
            interval = int(solver.NumArcs() / 20)
            for arc in range(solver.NumArcs()):
                if 0 < solver.Tail(arc) <= len(ref_map) and solver.Head(arc) != len(
                        start_nodes):
                    if solver.Flow(arc) > 0:
                        pixel = ref_map.worker(solver.Tail(arc))
                        comp = comp_map.task(solver.Head(arc),
                                             len(ref_map))
                        combined_value = CombinedEntry(path=comp.key, target=pixel.value)
                        solution.add(pixel.key, combined_value)
                if arc % interval == 0:
                    avg = (dt.now() - start).total_seconds() / (arc + 1)
                    rate = round(1 / avg, 1)
                    etr = timedelta(seconds=avg * (solver.NumArcs() - (arc + 1)))
                    logger.debug(f'rate: {rate}/s, estimated time remaining: {etr}')
            logger.debug('finished solving')
            return solution

    @classmethod
    def fill(cls, solution_map: SolutionMap, adjust=True):
        logger.debug('building image')
        canvas = Canvas(solution_map.bounds)
        for record in solution_map.records:
            component = Component(record.value.entries['path'].get())
            target = record.value.entries.get('target', None)
            img = component.adjust(
                *target.entry) if adjust and target is not None else component.img
            canvas.paste(record.key.x, record.key.y, img, record.value.entries['path'])
        logger.debug('image finished')
        return canvas


class Canvas(object):
    def __init__(self, size):
        self.ref_size = size
        self.w, self.h = size
        self.w *= constants.pixel_width
        self.h *= constants.pixel_height
        self.composite, self.component_id_array = Image.new('RGB', (self.w, self.h),
                                                            0), np.chararray(size)

    def paste(self, col, row, image, component_id):
        x_offset = col * constants.pixel_width
        y_offset = row * constants.pixel_height
        self.composite.paste(image, (x_offset, y_offset))
        self.component_id_array[col, row] = component_id

    def save(self, fn):
        self.composite.save(fn)
