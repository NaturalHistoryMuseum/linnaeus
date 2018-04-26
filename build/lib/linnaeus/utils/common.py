import cv2
import numpy as np


def hsv_pixels(img):
    pixels = np.array(img)
    hsv = cv2.cvtColor(pixels, cv2.COLOR_RGB2HSV_FULL)
    return hsv.reshape((-1, hsv.shape[-1]))
