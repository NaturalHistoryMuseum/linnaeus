import os

from linnaeus import Builder, ComponentCache, ReferenceImage

# PATH DEFINITIONS
# ----------------
root = '.'
# path to reference image
ref_image_path = os.path.join(root, 'refs/linnaeus.jpg')
# folder with the formatted components
component_image_dir = os.path.join(root, 'specimens')
# the name of the cache file doesn't really matter
cache_path = os.path.join(root, 'component.cache')
# 'map' csv files will be saved into/loaded from this folder
map_save_dir = os.path.join(root, 'maps')
# where to save the output
composite_save_path = os.path.join(root, 'outputs/composite.jpg')

# OBJECTS
# -------
# create a reference image object
ref = ReferenceImage(ref_image_path)
# create a cache to store the dominant hsv colour for each component
cache = ComponentCache(cache_path)
# create a 'builder' to construct the composite
builder = Builder(ref, cache)

# PROCESSING
# ----------
# load or create csv 'maps' of hsv values
ref_pixel_map, component_map = builder.load_maps(map_save_dir, component_image_dir)
# create a new blank 'canvas'
builder.new_composite()
# match the components to pixels and paste onto the canvas
builder.fill(ref_pixel_map, component_map, component_image_dir, map_save_dir)
# save the canvas
builder.save_composite(composite_save_path)
