import math

import numpy as np
from PIL import Image
from ortools.graph import pywrapgraph
from scipy import sparse
from sklearn.metrics.pairwise import pairwise_distances

from .config import ProgressLogger, constants, logger
from .models import CombinedEntry, Component, SolutionMap


def start_nodes(rows, cols):
    logger.debug('finding start nodes')
    return sparse.hstack(
        (np.zeros(rows), np.repeat(np.arange(1, rows + 1), cols),
         np.arange(rows + 1, rows + cols + 1))).T


def end_nodes(rows, cols):
    logger.debug('finding end nodes')
    return sparse.hstack((np.arange(1, rows + 1),
                          np.tile(np.arange(rows + 1, rows + cols + 1), rows),
                          np.repeat(rows + cols + 1, cols))).T


def costs(rows, cols, cost_matrix):
    logger.debug('finding arc costs')
    return sparse.hstack((np.zeros(rows), cost_matrix.flatten(), np.zeros(cols))).T


class Builder(object):
    @classmethod
    def cost_matrix(cls, ref_map, comp_map):
        ref_map.done()
        comp_map.done()
        logger.debug('building arrays')
        ref_records = sparse.csr_matrix([r.value.array for r in ref_map.records])
        comp_records = sparse.csr_matrix([r.value.array for r in comp_map.records])
        logger.debug('calculating cost matrix')
        xy = pairwise_distances(ref_records, comp_records)
        logger.debug('calculated distances - now normalising')
        cm = xy - xy.min()
        logger.debug('finished calculating cost matrix')
        return cm

    @classmethod
    def solve(cls, ref_map, comp_map):
        ref_map.done()
        comp_map.done()
        cost_matrix = cls.cost_matrix(ref_map, comp_map)
        rows, cols = cost_matrix.shape
        arc_count = rows + cols + (rows * cols)
        logger.debug(f'calculating {arc_count} arcs')
        arcs = sparse.hstack((start_nodes(rows, cols), end_nodes(rows, cols),
                              costs(rows, cols, cost_matrix)),
                             format='csr').astype(int)
        supplies = np.concatenate(([rows], np.zeros(rows + cols), [-rows])).astype(int)
        logger.debug('calculated arcs, now adding to solver')
        solver = pywrapgraph.SimpleMinCostFlow()
        with ProgressLogger(arc_count, 20) as p:
            block_size = 100000
            for i in range(int(math.ceil(arc_count / block_size))):
                start = i * block_size
                end = min((i + 1) * block_size, arc_count + 1)
                block = arcs[start:end].toarray()
                for arc in block:
                    solver.AddArcWithCapacityAndUnitCost(arc[0].item(), arc[1].item(), 1,
                                                         arc[2].item())
                    p.next()
        del arcs
        logger.debug('adding node supply')
        for i in range(supplies.size):
            solver.SetNodeSupply(i, np.asscalar(supplies[i]))
        logger.debug('solving')
        if solver.Solve() == solver.OPTIMAL:
            solution = SolutionMap()
            logger.debug('building solution map')
            logger.debug(f'processing {solver.NumArcs()} arcs')
            with ProgressLogger(solver.NumArcs(), 20) as p:
                for arc in range(solver.NumArcs()):
                    if 0 < solver.Tail(arc) <= len(ref_map) and solver.Head(
                            arc) != arc_count:
                        if solver.Flow(arc) > 0:
                            pixel = ref_map.worker(solver.Tail(arc))
                            comp = comp_map.task(solver.Head(arc),
                                                 len(ref_map))
                            combined_value = CombinedEntry(path=comp.key,
                                                           target=pixel.value)
                            solution.add(pixel.key, combined_value)
                    p.next()
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
