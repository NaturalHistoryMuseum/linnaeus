import numpy as np
from PIL import Image
from numba import njit
from ortools.graph import pywrapgraph
from scipy import sparse
from sklearn.metrics.pairwise import pairwise_distances

from .config import ProgressLogger, constants, logger
from .models import CombinedEntry, Component, SolutionMap


@njit
def plus(i, j):
    return i + j


@njit
def minus(i, j):
    return i - j


@njit
def multiply(i, j):
    return i * j


@njit
def get_ints(*x):
    return x


class Builder(object):
    @classmethod
    def cost_matrix(cls, ref_map, comp_map):
        logger.debug('building arrays')
        ref_records = sparse.csr_matrix([r.value.array for r in ref_map.records])
        comp_records = sparse.csr_matrix([r.value.array for r in comp_map.records])
        logger.debug('calculating cost matrix')
        xy = pairwise_distances(ref_records, comp_records)
        logger.debug('calculated distances - now normalising')
        cm = (xy - xy.min()).astype(int)
        logger.debug('finished calculating cost matrix')
        return cm

    @classmethod
    def solve(cls, ref_map, comp_map):
        if len(comp_map) > constants.max_components:
            logger.debug(
                f'trying to use {len(comp_map)} components will likely result in a '
                f'memory error: reducing to {constants.max_components}')
            comp_map.reduce(constants.max_components)
        cost_matrix = cls.cost_matrix(ref_map, comp_map)
        rows, cols = cost_matrix.shape
        cost_matrix = cost_matrix.reshape(-1, 1)
        arc_count = rows + cols + (rows * cols)
        supplies = np.concatenate(([rows], np.zeros(rows + cols), [-rows])).astype(int)
        logger.debug(f'adding {arc_count} arcs to solver ')
        solver = pywrapgraph.SimpleMinCostFlow()
        with ProgressLogger(arc_count, 20) as p:
            last_node = rows + cols + 1
            # section one
            for i in range(1, rows + 1):
                solver.AddArcWithCapacityAndUnitCost(0,
                                                     i,
                                                     1,
                                                     0)
                p.next()
            # section two
            colblock = np.arange(rows + 1, rows + cols + 1).reshape(-1, 1)
            for r in range(rows):
                rn = plus(r, 1)
                block_start = multiply(r, cols)
                block_end = plus(block_start, cols)
                block = np.concatenate((colblock,
                                        cost_matrix[block_start:block_end]), axis=1)
                for block_row in block:
                    c, cost = get_ints(*block_row)
                    solver.AddArcWithCapacityAndUnitCost(rn,
                                                         c,
                                                         1,
                                                         cost)
                    p.next()
            # section three
            for i in range(rows + 1, last_node):
                solver.AddArcWithCapacityAndUnitCost(
                    i,
                    last_node,
                    1,
                    0)
                p.next()
        logger.debug('adding node supply')
        for i in range(supplies.size):
            solver.SetNodeSupply(i, np.asscalar(supplies[i]))
        logger.debug('solving')
        sol = solver.Solve()
        if sol == solver.OPTIMAL:
            logger.debug('building solution map')
            logger.debug(f'processing {solver.NumArcs()} arcs')
            with ProgressLogger(solver.NumArcs(), 20) as p, SolutionMap() as solution:
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
            codes = {getattr(solver, i): i for i in dir(solver) if
                     not callable(getattr(solver, i)) and isinstance(getattr(solver, i),
                                                                     int)}
            print(codes[sol])
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
