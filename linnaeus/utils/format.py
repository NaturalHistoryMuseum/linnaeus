import cv2
import numpy as np
from matplotlib import pyplot as plt
from skimage import color, filters, measure, segmentation
from skimage.filters import gaussian
from skimage import feature, io
import os
import pickle
import pkg_resources

from linnaeus.config import constants


class Formatter(object):
    @classmethod
    def detect(cls, img):
        pixels = np.array(img)
        pixels = cls._exclude_colourscale(pixels)
        hsv = cv2.cvtColor(pixels, cv2.COLOR_RGB2HSV)
        hsv = gaussian(hsv, 5, multichannel=True) * 255
        hue = int(hsv[hsv[..., 1] > constants.saturation_threshold].mean(axis=0)[0])
        threshold = cv2.inRange(hsv, (0, constants.saturation_threshold, 0),
                                (hue, 255, 255))
        kernel = np.ones((3, 3), np.uint8)
        opening = cv2.morphologyEx(threshold, cv2.MORPH_OPEN, kernel, iterations=5)
        dilated = cv2.dilate(opening, kernel, iterations=5)
        im, contours, hier = cv2.findContours(dilated, cv2.RETR_EXTERNAL,
                                               cv2.CHAIN_APPROX_SIMPLE)
        try:
            largest_contour = sorted(contours, key=lambda c: cv2.contourArea(c))[-1]
            x, y, w, h = cv2.boundingRect(largest_contour)
            assert w > constants.pixel_size and h > constants.pixel_size
            img = img.crop((x, y, x + w, y + h))
        except IndexError or AssertionError:
            pass
        return img

    @staticmethod
    def _exclude_colourscale(pixels):
        b = 50
        img_h, img_w = pixels.shape[:2]
        pixels = gaussian(pixels, 3, multichannel=True)

        with open(pkg_resources.resource_filename('linnaeus', 'utils/scales.pkl'), 'rb') as f:
            scales = pickle.load(f)

        for scale in scales:
            pattern = gaussian(scale, 3, multichannel=True)
            h, w = pattern.shape[:2]
            if h > img_h or w > img_w:
                continue
            result = feature.match_template(pixels, pattern)[..., 0]
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
        with open(root + '.pkl', 'wb') as f:
            pickle.dump(scales, f)

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
