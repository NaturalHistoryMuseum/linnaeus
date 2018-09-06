# Example

The example uses this painting of Carl Linnaeus as a reference image:
![Carl Linnaeus](refs/linnaeus.jpg)

The component images are a subset of specimen images (roughly 15,000) downloaded from the NHM's [Data Portal](http://data.nhm.ac.uk), like this one:
![Odontopera bidentata](http://www.nhm.ac.uk/services/media-store/asset/7364c60db49610b3ec31d854f0972d20c61fcd0c/contents/thumbnail)

Except cropped and resized to 50x50 squares (see the `Formatter` utility):
![An array of resized specimen images](../docs/specimens.fe92027e.jpg)

These resized component images can be found in the `specimens.zip` file.

The configuration file should be named `.config` and be inside your working directory. If you're fine with the defaults (shown below) then you don't have to have a config file.

The config file syntax looks like this (and these are the default values):

```yaml
# the width and height of each component image (they must be square)
pixel_size: 50

# the maximum number of component images in the final output
max_ref_size: 8000

# used for the downloader but not a lot else
saturation_threshold: 50

# the maximum component pool size - e.g. if you have 200k component images the program will randomly choose 80k of them
max_components: 80000

# set to warn or lower(?) to turn off progress updates
log_level: debug

# method for determining the dominant colour in an image: either 'average' or 'round'
dominant_colour_method: average
```

So the example project structure looks like this at the start of the first build:

```
example/
    refs/
        linnaeus.jpg
    specimens/
        00003cc8177c991aa5052cd4d4429edf5688162f.jpg
        00008d8ede2775f76bc89870bc22e207393a6d37.jpg
        00009351cb88e82fea0ebd1530b8158be665329a.jpg
        0000a2636bfac0ec061948246c16c006c75744cc.jpg
        000122b3ea236252944a992c01f25b3c2ee731e8.jpg
        ...
    .config
    main.py
```

## The script

The code for running a build can be fairly short:

```python
from linnaeus import Builder, MapFactory

# PATH DEFINITIONS
# ----------------
ref_image_path = './refs/linnaeus.jpg'  # path to reference image
component_image_dir = './specimens'  # folder with the formatted components
composite_save_path = './composite.jpg'  # where to save the output

# MAP GENERATION
# -------
# create a reference map
ref = MapFactory.reference().from_image_local(ref_image_path)
# create a component map
comp = MapFactory.component().from_local(folders=[component_image_dir])

# PROCESSING
# ----------
# find the solution from the maps
solution = Builder.solve(ref, comp)
# use the solution map to fill a canvas
canvas = Builder.fill(solution)
# save the canvas
canvas.save(composite_save_path)
```

A more complete example (including saving/loading maps) can be found in `example/main.py`.

## Running

You can then just run your script as normal, e.g.

```bash
python your_script.py
```

On first running, it may take a while - this example took around half an hour. The example folder in this repo includes all the maps for `linnaeus.jpg`, so if you just want to run the example it should only take about 30 seconds.

## Using the CLI

<p align="center">
    <img src="https://cdn.rawgit.com/NaturalHistoryMuseum/linnaeus/master/example/demo.svg">
</p>