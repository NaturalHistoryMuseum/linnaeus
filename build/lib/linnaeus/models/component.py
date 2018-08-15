import numpy as np
from PIL import Image, ImageChops

from linnaeus import common
from linnaeus.config import constants
from linnaeus.utils import Formatter


class Component(object):
    def __init__(self, img: Image, location=None):
        if img.mode != 'RGB':
            img = img.convert('RGB')
        self.img = Formatter.resize(img)
        self.location = location

        self.array = np.array(self.img)
        self._dominant = None

    def _get_dominant(self, f):
        hsv = common.hsv_pixels(self.img)
        data = np.array([tuple(p) for p in hsv if f(p)])
        if len(data) == 0:
            return None, None, None
        if constants.dominant_colour_method == 'round':
            rounded = (data / 20).round(0) * 20
            freq = np.unique(rounded, axis=0, return_counts=True)
            most_freq = freq[0][np.where(freq[1] == freq[1].max())].tolist()
            mask = np.apply_along_axis(lambda x: x.tolist() in most_freq, 1,
                                       rounded)
            dom = data[mask].mean(axis=0).astype(int).tolist()
        else:
            # avg
            dom = data.mean(axis=0).astype(int).tolist()
        return dom

    @property
    def dominant(self):
        if self._dominant is None:
            self._dominant = self._get_dominant(lambda x: True)
        return self._dominant

    def adjust(self, h, s, v):
        """Adjusts the image to make the dominant colour the same as the target.

        :param h: the target hue (0 - 255)
        :param s: the target saturation (0 - 255)
        :param v: the target value (0 - 255)
        :return: the adjusted image as a PIL Image object
        """
        ch, cs, cv = self.dominant
        add_hsv = [0, 0, 0]
        subtract_hsv = [0, 0, 0]
        stats = [(h, ch), (s, cs),
                 (v, cv)]
        for i in range(len(stats)):
            target, current = stats[i]
            err = abs(target - current)
            if target > current:
                add_hsv[i] = err
            else:
                subtract_hsv[i] = err

        add_overlay = Image.new('HSV', self.img.size, color=tuple(add_hsv)).convert(
            'RGB')
        subtract_overlay = Image.new('HSV', self.img.size,
                                     color=tuple(subtract_hsv)).convert('RGB')
        img = ImageChops.add(self.img, add_overlay)
        img = ImageChops.subtract(img, subtract_overlay)
        return img

    def resize(self):
        return self.img.resize(constants.pixel_size)
