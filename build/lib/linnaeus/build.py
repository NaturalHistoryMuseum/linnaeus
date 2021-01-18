import numpy as np
from PIL import Image
from numba import njit
from ortools.graph import pywrapgraph
from scipy import sparse
from sklearn.metrics.pairwise import pairwise_distances

from .config import ProgressLogger, TimeLogger, constants, logger
from .models import CombinedEntry, Component, HsvEntry, SolutionMap


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
    def cost_matrix(cls, ref_map, comp_map, use_mask=True, mask_tolerance=0):
        logger.debug('building arrays')
        ref_records = sparse.csr_matrix([r.value.array for r in ref_map.records])
        comp_records = sparse.csr_matrix([r.value.array for r in comp_map.records])
        logger.debug('calculating cost matrix')
        xy = pairwise_distances(ref_records, comp_records)
        logger.debug('normalising cost matrix')
        cm = (xy.T - xy.min(axis=1)).T.astype(int)
        r, c = cm.shape
        if use_mask:
            logger.debug('masking cost matrix')
            logger.info('calculating distance from mean')
            deviance = np.ma.array(cm).anom(axis=1)
            logger.info('adjusting distance matrix')
            deviance = (deviance.T - (deviance.std(axis=1) * mask_tolerance)).T
            logger.info('masking items')
            cm_mask = np.ma.masked_less_equal(deviance, 0).mask
            if not (cm_mask.sum(axis=1) > 0).all():
                raise SolveError(None, masked=True, msg='Mask tolerance too low.')
            cm_nonzero = cm_mask.nonzero()
            logger.info('applying mask to cost matrix')
            masked = cm[cm_nonzero]
            row, col = cm_nonzero
            logger.info('adjusting row/col indices')
            row = row + 1
            col = col + r + 1
            logger.info('grouping')
            cm = np.dstack((row, col, masked))[0]
        else:
            cm = cm.reshape(-1, 1)
        logger.debug('finished calculating cost matrix')
        return cm, r, c

    @classmethod
    def solve(cls, ref_map, comp_map, use_mask=True, mask_tolerance=0):
        if len(comp_map) > constants.max_components:
            logger.debug(
                f'trying to use {len(comp_map)} components will likely result in a '
                f'memory error: reducing to {constants.max_components}')
            comp_map.reduce(constants.max_components)
        cost_matrix, rows, cols = cls.cost_matrix(ref_map, comp_map, use_mask,
                                                  mask_tolerance)
        cost_arcs = cost_matrix.shape[0]
        arc_count = rows + cols + cost_arcs
        supplies = np.concatenate(([rows], np.zeros(rows + cols), [-rows])).astype(int)
        logger.debug(f'adding {arc_count} arcs to solver ')
        solver = pywrapgraph.SimpleMinCostFlow()
        logger.debug(f'section 1: {rows} items')
        with ProgressLogger(rows, 2) as p:
            last_node = rows + cols + 1
            # section one
            for i in range(1, rows + 1):
                solver.AddArcWithCapacityAndUnitCost(0,
                                                     i,
                                                     1,
                                                     0)
                p.next()
        logger.debug(f'section 2: {cost_arcs} items')
        with ProgressLogger(cost_arcs, 20) as p:
            # section two
            if use_mask:
                for n in cost_matrix:
                    r, c, cost = get_ints(*n)
                    solver.AddArcWithCapacityAndUnitCost(r,
                                                         c,
                                                         1,
                                                         cost)
                    p.next()
            else:
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
        logger.debug(f'section 3: {cols} items')
        with ProgressLogger(cols, 3) as p:
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
        with TimeLogger():
            status = solver.Solve()
        if status == solver.OPTIMAL:
            logger.debug('building solution map')
            logger.debug(f'processing {solver.NumArcs()} arcs')
            with ProgressLogger(solver.NumArcs(), 20) as p, SolutionMap() as solution:
                ref_map_len = len(ref_map)
                for arc in range(solver.NumArcs()):
                    t = solver.Tail(arc)
                    h = solver.Head(arc)
                    f = solver.Flow(arc)
                    if 0 < t <= ref_map_len and h != arc_count and f > 0:
                        pixel = ref_map.worker(t)
                        comp = comp_map.task(h, ref_map_len)
                        combined_value = CombinedEntry(path=comp.key,
                                                       target=pixel.value,
                                                       src=comp.value)
                        solution.add(pixel.key, combined_value)
                    p.next()
                logger.debug('finished solving')
                logger.debug(f'assigned {len(solution)} pixels from a pool of '
                             f'{constants.max_components} specimen images')
                return solution
        else:
            raise SolveError(status, use_mask)

    @classmethod
    def silhouette(cls, ref_map, comp_map):
        logger.debug('building arrays')
        comp_records = np.c_[
            np.arange(len(comp_map)), [r.value.array for r in comp_map.records]]
        logger.debug('choosing random sample')
        parsort = np.random.choice(comp_records[:,0], len(ref_map))
        comp_records = comp_records[parsort]
        if len(comp_records) < len(ref_map):
            raise SolveError
        np.random.shuffle(comp_records)
        logger.debug('building solution map')
        logger.debug(f'assigning {len(ref_map)} pixels')
        with ProgressLogger(len(ref_map), 20) as p, SolutionMap() as solution:
            for i, pixel in enumerate(ref_map.records):
                comp = comp_map.records[comp_records[i, 0]]
                combined_value = CombinedEntry(path=comp.key,
                                               target=HsvEntry(0, 0, 0),
                                               src=comp.value)
                solution.add(pixel.key, combined_value)
                p.next()
        logger.debug('finished solving')
        logger.debug(f'assigned {len(solution)} pixels from a pool of '
                     f'{len(comp_map)} specimen images')
        return solution

    @classmethod
    def fill(cls, solution_map: SolutionMap, adjust=True, prefix=None):
        logger.debug('building image')
        canvas = Canvas(solution_map.bounds)
        with ProgressLogger(len(solution_map), 10) as p:
            for record in solution_map.records:
                entries = record.value.entries
                colour = entries.get('src', None)
                component = Component(entries['path'].get(prefix),
                                      dominant_colour=colour.array
                                      if colour is not None else None)
                target = entries.get('target', None)
                img = component.adjust(
                    *target.entry) if adjust and target is not None else component.img
                canvas.paste(record.key.x, record.key.y, img, entries['path'])
                p.next()
        logger.debug('image finished')
        return canvas


class Canvas(object):
    def __init__(self, size):
        self.ref_size = size
        self.w, self.h = size
        self.w *= constants.pixel_size
        self.h *= constants.pixel_size
        self.composite, self.component_id_array = Image.new('RGBA', (self.w, self.h),
                                                            0), np.chararray(size)

    def paste(self, col, row, image, component_id):
        x_offset = col * constants.pixel_size
        y_offset = row * constants.pixel_size
        self.composite.paste(image, (x_offset, y_offset))
        self.component_id_array[col, row] = component_id

    def save(self, fn):
        if not fn.endswith('.png'):
            self.composite = self.composite.convert(mode='RGB')
        self.composite.save(fn)


class SolveError(Exception):
    def __init__(self, error_code, masked, msg=None):
        self.error_code = error_code
        self.reason = self.codes(error_code)
        self.masked = masked
        if msg is None:
            msg = f'Failed to solve: {self.reason}.'
            if self.masked:
                msg += ' Try passing "use_mask=False" into the build method, ' \
                       'or increase "mask_tolerance".'
        super(SolveError, self).__init__(msg)

    @staticmethod
    def codes(error_code):
        solve_cls = pywrapgraph.SimpleMinCostFlow
        codes = {getattr(solve_cls, i): i for i in dir(solve_cls) if
                 not callable(getattr(solve_cls, i)) and isinstance(
                     getattr(solve_cls, i),
                     int)}
        return codes.get(error_code, 'UNKNOWN ERROR')
