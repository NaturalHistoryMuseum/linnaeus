import math

import cv2
import numpy as np
import matplotlib.pyplot as plt
from linnaeus import MapFactory, utils
from linnaeus.config import ProgressLogger


def cleaner(path, records, commit=False, block_size=30):
    m = MapFactory.component().deserialise(MapFactory.load_text(path))
    print(f'{len(records)}/{len(m)} matching items.')
    while not commit:
        n_start = len(records)
        records_copy = records.copy()
        keep_round = []
        for b in range(0, len(records), block_size):
            block_end = min(block_size, len(records))
            block = records_copy[:block_end]
            del records_copy[:block_end]
            utils.thumbnails(block, max_size=8000, ncols=16)
            block_delete = input('delete these? [y/N] ') == 'y'
            if not block_delete:
                usrinput = input(
                    'enter the index(es) of the component(s) TO KEEP, separated by '
                    'spaces (don\'t worry if you miss any, I\'ll ask again before '
                    'deleting) or \'A\' to keep all of them: ').split(' ')
            else:
                continue
            if usrinput[0] == 'A':
                keep_these = list(range(block_size))
            elif usrinput[0] == '-':
                delete_these = [int(x) for x in usrinput[1:]]
                keep_these = [i for i in range(block_size) if
                              i not in delete_these]
            else:
                keep_these = []
                for x in usrinput:
                    if ':' in x:
                        s, f = x.split(':', 1)
                        keep_these += list(range(int(s), int(f) + 1))
                    else:
                        try:
                            keep_these.append(int(x))
                        except ValueError:
                            continue
            keep_round += keep_these
        for i in sorted(keep_round, reverse=True):
            del records[i]
        n_end = len(records)
        print(f'removed {n_start - n_end} records in that round.')
        commit = n_start == n_end
    if commit:
        print('deleting from map.')
        MapFactory.save_text(path + '.dirty', m.serialise())
        c = 0
        with m:
            for r in records:
                m.remove(r)
                print(f'{c}: {r}')
                c += 1
        MapFactory.save_text(path, m.serialise())


def clean_colour(path, commit=False, block_size=30, h=None, s=None, v=None, ht=5, st=5,
                 vt=5):
    m = MapFactory.component().deserialise(MapFactory.load_text(path))
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
        cleaner(path, matches, commit, block_size)
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


def angle_cos(p0, p1, p2):
    d1, d2 = (p0 - p1).astype('float'), (p2 - p1).astype('float')
    return abs(np.dot(d1, d2) / np.sqrt(np.dot(d1, d1) * np.dot(d2, d2)))


def clean_squares(path, commit=False, block_size=80):
    m = MapFactory.component().deserialise(MapFactory.load_text(path))
    matches = []
    max_batch = block_size * 3
    with ProgressLogger(max_batch, 20) as p, open('/home/ginger/logs/sq.log', 'w') as f:
        for r in m.records:
            img = cv2.imread(r.key.entry)
            greyscale = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            blurred = cv2.GaussianBlur(greyscale, (5, 5), 0)
            thresh = cv2.threshold(blurred, 60, 255, cv2.THRESH_BINARY)[1]
            _, contours, hierarchy = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
                                                      cv2.CHAIN_APPROX_SIMPLE)
            for c in contours:
                contour_length = cv2.arcLength(c, True)
                approx = cv2.approxPolyDP(contours[0], 0.02 * contour_length, True)
                if len(approx) == 4 and cv2.contourArea(
                        approx) > 200 and cv2.isContourConvex(approx):
                    approx = approx.reshape(-1, 2)
                    max_cos = np.max(
                        [angle_cos(approx[i], approx[(i + 1) % 4], approx[(i + 2) % 4])
                         for i in range(4)])
                    if max_cos < 0.1:
                        f.write(f'{r.key.entry}: {max_cos}\n')
                        matches.append((r, max_cos))
                        p.next()
                        break
            if len(matches) >= max_batch:
                break
    if len(matches) > 0:
        matches = [x[0] for x in sorted(matches, key=lambda x: x[1])]
        cleaner(path, matches, commit, block_size)
    else:
        print('no matches found.')


def clean_by_histogram(path, input_img_path, commit=False, block_size=320):
    m = MapFactory.component().deserialise(MapFactory.load_text(path))
    matches = []
    input_img = cv2.imread(input_img_path)
    input_hist = cv2.calcHist([input_img], [0, 1, 2], None, [8, 8, 8], [0, 256, 0, 256, 0, 256])
    input_hist = cv2.normalize(input_hist, None).flatten()
    with ProgressLogger(len(m), 10) as p:
        for r in m.records:
            img = cv2.imread(r.key.entry)
            hist = cv2.calcHist([img], [0, 1, 2], None, [8, 8, 8],
                        [0, 256, 0, 256, 0, 256])
            hist = cv2.normalize(hist, None).flatten()
            d = cv2.compareHist(input_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
            if d < 0.4:
                matches.append((r, d))
            p.next()
    if len(matches) > 0:
        matches = [x[0] for x in sorted(matches, key=lambda x: x[1])]
        cleaner(path, matches, commit, block_size)
    else:
        print('no matches found.')
