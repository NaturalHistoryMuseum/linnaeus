import cv2
import numpy as np


def hsv_pixels(img):
    pixels = np.array(img)
    hsv = cv2.cvtColor(pixels, cv2.COLOR_RGB2HSV_FULL)
    return hsv.reshape((-1, hsv.shape[-1]))


def hsv_pixels_with_xy(img):
    pixels = np.array(img)
    hsv = []
    r = 0
    for row in cv2.cvtColor(pixels, cv2.COLOR_RGB2HSV_FULL):
        c = 0
        for col in row:
            hsv.append(np.append(col, np.array([c, r])))
            c += 1
        r += 1
    hsv = np.array(hsv).astype(int)
    return hsv.reshape((-1, hsv.shape[-1]))
