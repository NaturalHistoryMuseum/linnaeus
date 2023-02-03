import cv2
import numpy as np
from matplotlib import pyplot as plt
from skimage import color, filters, measure, segmentation
from skimage.filters import gaussian
from skimage import feature, io
import os
import pickle
import pkg_resources
from PIL import Image

from linnaeus.config import constants


class Formatter(object):
    def __init__(self):
        self._colour_scales = None

    @property
    def colour_scales(self):
        if self._colour_scales is None:
            with open(pkg_resources.resource_filename('linnaeus', 'utils/scales.pkl'), 'rb') as f:
                self._colour_scales = pickle.load(f)
        return self._colour_scales

    def detect(self, img):
        w, h = img.size
        # resize the image to about 2x the size of the desired 'pixel' size;
        # captures more of the image while still allowing us to avoid unwanted
        # parts like labels and scales
        target_size = int(constants.pixel_size * 2)
        adj = max(target_size / w, target_size / h)
        w = int(w * adj)
        h = int(h * adj)
        img = img.resize((w, h))
        pixels = np.array(img)
        hsv = cv2.cvtColor(pixels, cv2.COLOR_RGB2HSV)
        hsv = (gaussian(hsv, 5, multichannel=True) * 255).astype(int)

        # extract (overlapping) square blocks of the 'pixel' size
        sections = []
        move_size = constants.pixel_size // 3
        x1 = 0
        while (x1 + constants.pixel_size) < w:
            y1 = 0
            while (y1 + constants.pixel_size) < h:
                section = hsv[y1:y1 + constants.pixel_size, x1:x1 + constants.pixel_size]
                sections.append({
                    'img': pixels[y1:y1 + constants.pixel_size, x1:x1 + constants.pixel_size],
                    'hsv': section.reshape((-1, 3)).mean(axis=0).astype(int),
                    'std': section.reshape((-1, 3)).std(axis=0).astype(int)
                })
                y1 += move_size
            x1 += move_size

        # use the section with the least variation in hue (and if multiple are
        # tied, use the one with the most saturation)
        # hopefully this should exclude any colour scales and be the most
        # representative of the image as a whole, though ymmv
        sections = sorted(sections, key=lambda s: (s['std'][0], -s['hsv'][1]))
        return Image.fromarray(sections[0]['img'])

    def _exclude_colourscale(self, pixels):
        b = 50
        img_h, img_w = pixels.shape[:2]
        pixels = gaussian(pixels, 3, multichannel=True)

        for scale in self.colour_scales:
            fig, axes = plt.subplots(ncols=2)
            pattern = scale
            axes[0].imshow(pattern)
            h, w = pattern.shape[:2]
            if h > img_h or w > img_w:
                continue
            result = feature.match_template(pixels, pattern)[..., 0]
            axes[1].imshow(result)
            plt.show()
            peak = result.max()
            ij = np.unravel_index(np.argmax(result), result.shape)
            x, y = ij[::-1]
            if peak >= 0.8:
                y1 = max(y-b, 0)
                y2 = min(y+h+b, img_h)
                x1 = max(x-b, 0)
                x2 = min(x+w+b, img_w)
                pixels[y1:y2, x1:x2] = color.grey2rgb(color.rgb2grey(pixels[y1:y2, x1:x2]))

        return (pixels * 255).astype(np.uint8)

    @classmethod
    def genscales(cls):
        root = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'scales')
        scales = [os.path.join(root, f) for f in os.listdir(root)]
        scales = [gaussian(io.imread(scale), 3) for scale in scales]
        rotated_scales = []
        for scale in scales:
            rotated_scales.append(scale)
            for _ in range(3):
                scale = np.rot90(scale)
                rotated_scales.append(scale)
        with open(root + '.pkl', 'wb') as f:
            pickle.dump(rotated_scales, f)

    @classmethod
    def rotate(cls, img):
        w, h = img.size
        if h > w:
            img = img.rotate(90, expand=1)
        return img

    @classmethod
    def resize(cls, img):
        w, h = img.size
        if w == constants.pixel_size and h == constants.pixel_size:
            return img
        adj = max(constants.pixel_size / w, constants.pixel_size / h)
        w = int(w * adj)
        h = int(h * adj)
        img = img.resize((w, h))
        x_pad = (w - constants.pixel_size) // 2
        y_pad = (h - constants.pixel_size) // 2
        img = img.crop((
            x_pad,
            y_pad,
            x_pad + constants.pixel_size,
            y_pad + constants.pixel_size
            ))
        return img
