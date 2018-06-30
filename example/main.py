import os

from linnaeus import Builder, MapFactory, SolveError

# PATH DEFINITIONS
# ----------------
root = '.'
ref_image_path = os.path.join(root, 'refs/linnaeus.jpg')
# best to use local files for the components rather than the url or API methods
component_image_dir = os.path.join(root, 'specimens')
# where to save the output
composite_save_path = os.path.join(root, 'outputs/new_composite.jpg')
# where to save the maps
map_save_dir = os.path.join(root, 'maps')
ref_map_save_path = os.path.join(map_save_dir, 'ref.json')
comp_map_save_path = os.path.join(map_save_dir, 'comp.json')
sol_map_save_path = os.path.join(map_save_dir, 'solution.json')

# MAPS
# ----
if os.path.exists(ref_map_save_path):
    # load a reference map
    reference_map = MapFactory.reference().deserialise(
        MapFactory.load_text(ref_map_save_path))
else:
    # make a new reference map
    reference_map = MapFactory.reference().from_image_local(ref_image_path)
    # and save it
    MapFactory.save_text(ref_map_save_path, reference_map.serialise())

if os.path.exists(comp_map_save_path):
    # load a component map
    component_map = MapFactory.component().deserialise(
        MapFactory.load_text(comp_map_save_path))
else:
    # make a new component map
    component_map = MapFactory.component().from_local(folders=[component_image_dir])
    # and save it
    MapFactory.save_text(comp_map_save_path, component_map.serialise())

# PROCESSING
# ----------
# find the solution from the maps
if os.path.exists(sol_map_save_path):
    # load a component map
    solution_map = MapFactory.solution().deserialise(
        MapFactory.load_text(sol_map_save_path))
else:
    # make a new solution map
    try:
        # use masking to ignore components that are unlikely to match - this is much
        # faster but more likely to fail
        # (the lower the mask_tolerance, the more components will be ignored)
        solution_map = Builder.solve(reference_map, component_map, use_mask=True,
                                     mask_tolerance=-1)
    except SolveError:
        # try again without masking
        solution_map = Builder.solve(reference_map, component_map, use_mask=False)
    # save the solution
    MapFactory.save_text(sol_map_save_path, solution_map.serialise())

# use the solution map to fill a canvas
canvas = Builder.fill(solution_map, adjust=True)
# save the canvas
canvas.save(composite_save_path)
