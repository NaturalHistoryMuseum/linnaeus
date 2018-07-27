import math

from matplotlib import pyplot as plt
from PIL import Image
import numpy as np
from linnaeus.config import constants


def thumbnails(records, fn=None, ncols=3, title=True, max_size=65536):
    nrows = int(math.ceil(len(records) / ncols))
    h = constants.pixel_height * nrows
    w = constants.pixel_width * ncols
    if max_size > 65536:
        max_size = 65536
    if h > (max_size / 100) or w > (max_size / 100):
        adj = (max_size / 100) / max(w, h)
        w = int(w * adj)
        h = int(h * adj)
    fig, axes = plt.subplots(ncols=ncols, nrows=nrows, figsize=(w, h))
    if len(axes.shape) == 1:
        axes = axes.reshape(1, -1)

    for r in range(nrows):
        for c in range(ncols):
            i = (r * ncols) + c
            axes[r, c].axis('off')
            if len(records) == 0:
                break
            record = records.pop(0)
            img = np.array(Image.open(record.key.entry))
            if title:
                axes[r, c].set_title(i, {'fontsize': 20})
            print(f'{i}: {record.key.entry}')
            axes[r, c].imshow(img)

    #fig.subplots_adjust(left=0.05, right=0.95, bottom=0.02, top=0.95)
    if fn is not None:
        fig.savefig(fn, transparent=True)
    else:
        fig.show()