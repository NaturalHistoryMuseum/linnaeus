import math

from linnaeus import MapFactory, utils


def clean_colour(path, commit=True, **kwargs):
    m = MapFactory.component().deserialise(MapFactory.load_text(path))
    h = kwargs.get('h', None)
    s = kwargs.get('s', None)
    v = kwargs.get('v', None)
    ht = kwargs.get('ht', 5)
    st = kwargs.get('st', 5)
    vt = kwargs.get('vt', 5)
    matches = []
    for r in m.records:
        h_pass = (h is not None and math.isclose(r.value.h, h,
                                                 abs_tol=ht)) or h is None
        s_pass = (s is not None and math.isclose(r.value.s, s,
                                                 abs_tol=st)) or s is None
        v_pass = (v is not None and math.isclose(r.value.v, v,
                                                 abs_tol=vt)) or v is None
        if h_pass and s_pass and v_pass:
            matches.append(r)
    if len(matches) > 0:
        print(f'{len(matches)}/{len(m)} matching items.')
        while not commit:
            utils.thumbnails(matches.copy(), max_size=5000)
            commit = input('delete these? [y/N] ') == 'y'
            if commit:
                break
            keep_these = input(
                'enter the index(es) of the component(s) TO KEEP, separated by '
                'spaces: ').split(
                ' ')
            for i in sorted([int(x) for x in keep_these], reverse=True):
                del matches[i]
        if commit:
            print('deleting from map.')
            MapFactory.save_text(path + '.dirty', m.serialise())
            c = 0
            with m:
                for r in matches:
                    m.remove(r)
                    print(f'{c}: {r}')
                    c += 1
            MapFactory.save_text(path, m.serialise())
    else:
        print('no matches found.')


def clean_similar_to(solution_path, component_path, row, col, commit=True):
    solution = MapFactory.solution().deserialise(MapFactory.load_text(solution_path))
    components = MapFactory.component().deserialise(MapFactory.load_text(component_path))
    pixel = next(i for i in solution.records if i.key.x == col and i.key.y == row)
    comp = next(
        i for i in components.records if i.key.path == pixel.value.entry['path'])
    print(f'hsv: {comp.value.h}, {comp.value.s}, {comp.value.v}')
    clean_colour(component_path, commit, h=comp.value.h, s=comp.value.s, v=comp.value.v)
