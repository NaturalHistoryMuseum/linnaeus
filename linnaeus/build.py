from datetime import datetime as dt, timedelta

import numpy as np
from PIL import Image
from ortools.graph import pywrapgraph
from scipy.spatial.distance import cdist

from .config import constants, logger
from .models import CombinedEntry, Component, SolutionMap


class Builder(object):
    @classmethod
    def cost_matrix(cls, ref_map, comp_map):
        ref_map.done()
        comp_map.done()
        logger.debug('building arrays')
        ref_records = np.array([r.value.array for r in ref_map.records])
        comp_records = np.array([r.value.array for r in comp_map.records])
        logger.debug('calculating cost matrix')
        xy = cdist(ref_records, comp_records)
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
        arcs = np.stack((
            np.concatenate((np.zeros(rows), np.repeat(np.arange(1, rows + 1), cols),
                            np.arange(rows + 1, rows + cols + 1))),
            np.concatenate((np.arange(1, rows + 1),
                            np.tile(np.arange(rows + 1, rows + cols + 1), rows),
                            np.repeat(rows + cols + 1, cols))),
            np.concatenate((np.zeros(rows), cost_matrix.flatten(), np.zeros(cols)))
            ), axis=1).astype(int)
        supplies = np.concatenate(([rows], np.zeros(rows + cols), [-rows])).astype(int)
        for a in arcs:
            a = a.tolist()
            solver.AddArcWithCapacityAndUnitCost(a[0], a[1], 1, a[2])
        for i in range(supplies.size):
            solver.SetNodeSupply(i, np.asscalar(supplies[i]))
        logger.debug('solving')
        if solver.Solve() == solver.OPTIMAL:
            solution = SolutionMap()
            logger.debug('building solution map')
            start = dt.now()
            logger.debug(f'processing {solver.NumArcs()} arcs')
            interval = int(solver.NumArcs() / 20)
            for arc in range(solver.NumArcs()):
                if 0 < solver.Tail(arc) <= len(ref_map) and solver.Head(arc) != len(
                        arcs):
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
        else:
            raise Exception('failed to solve')

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
