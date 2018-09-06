import cv2
import numpy as np

from linnaeus.config import constants


class Formatter(object):
    @classmethod
    def detect(cls, img):
        pixels = np.array(img)
        hsv = cv2.cvtColor(pixels, cv2.COLOR_RGB2HSV)
        threshold = cv2.inRange(hsv, (0, constants.saturation_threshold, 0),
                                (255, 255, 255))
        kernel = np.ones((3, 3), np.uint8)
        opening = cv2.morphologyEx(threshold, cv2.MORPH_OPEN, kernel, iterations=5)
        dilated = cv2.dilate(opening, kernel, iterations=5)
        img, contours, hier = cv2.findContours(dilated, cv2.RETR_EXTERNAL,
                                               cv2.CHAIN_APPROX_SIMPLE)
        try:
            largest_contour = sorted(contours, key=lambda c: cv2.contourArea(c))[-1]
            x, y, w, h = cv2.boundingRect(largest_contour)
            img = img.crop((x, y, x + w, y + h))
        except IndexError:
            pass
        return img

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
