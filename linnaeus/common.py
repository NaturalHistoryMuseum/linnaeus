import cv2
import numpy as np


def convert_to_hsv(img):
    pixels = np.array(img)
    return cv2.cvtColor(pixels, cv2.COLOR_RGB2HSV_FULL)


def hsv_pixels(img):
    hsv = convert_to_hsv(img)
    return hsv.reshape((-1, hsv.shape[-1]))


def hsv_pixels_with_xy(img):
    hsv = []
    r = 0
    for row in convert_to_hsv(img):
        c = 0
        for col in row:
            hsv.append(np.append(col, np.array([c, r])))
            c += 1
        r += 1
    hsv = np.array(hsv).astype(int)
    return hsv.reshape((-1, hsv.shape[-1]))


def tryint(i):
    try:
        if isinstance(i, np.generic):
            return np.asscalar(i)
        else:
            return int(i)
    except ValueError:
        return i
