from linnaeus.config import ProgressLogger
from linnaeus.models import CombinedEntry, SolutionMap
from linnaeus import MapFactory


def add_src(solution_map, component_map, save_as):
    with SolutionMap() as new_solution, ProgressLogger(len(solution_map), 10) as p:
        for record in solution_map.records:
            if 'src' in record.value.entries:
                new_solution.add(record.key, record.value)
                p.next()
                continue
            component = component_map[record.value.entries['path']]
            new_solution.add(record.key, CombinedEntry(path=component.key,
                                                       target=record.value.entries[
                                                           'target'],
                                                       src=component.value))
            p.next()
    MapFactory.save_text(save_as, new_solution.serialise())
