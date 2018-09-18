import math

import cv2
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage import filters, future
from skimage.morphology import disk, watershed


def show(img):
    """
    Helper/debugging method for displaying images.
    :param img: image as numpy array
    """
    plt.imshow(img)
    plt.axis('off')
    plt.tight_layout()
    plt.show()


def draw_contour(contour, img, fill=False):
    """
    Helper/debugging method for drawing contours.
    :param contour: a numpy array of n (x,y) points in the shape (n,1,2)
    :param img: the image to draw on, as a numpy array
    :param fill: boolean indicating whether to display the contour as a filled contour
                 (True) or just the outline (False)
    """
    cimg = img.copy()
    show(cv2.drawContours(cimg, [contour], 0, (255, 0, 125), -1 if fill else 2))


def colourspace(pixels, space):
    """
    Use opencv to change the colour space (e.g. RGB, HSV) of a set of pixels.
    :param pixels: a list or array of pixels that can be cast to the shape (n, 1, 3)
    :param space: the opencv colour space constant, e.g. cv2.COLOR_RGB2HSV
    :return: a numpy array of converted pixels
    """
    carray = np.array(pixels).reshape(-1, 1, 3).astype(np.uint8)
    return cv2.cvtColor(carray,
                        space)


class BackgroundRemover(object):
    def __init__(self, original, bg_image=None, colour=(0, 0, 255),
                 variance=(50, 50, 50)):
        """
        Initialises the BackgroundRemover class, which attempts to remove plain
        backgrounds from images.
        :param original: the input image
        :param bg_image: (optional) a background image to compare against
        :param colour: the background colour (defaults to white)
        :param variance: a measure of how much the background colour varies
        """
        self.original = original
        self.colour = np.array(colour)
        self.contrast = np.array((179 - colour[0], 255, 255 - colour[2]))
        self.variance = np.array(variance)
        self.rgb_colour = colourspace(self.colour, cv2.COLOR_HSV2RGB_FULL)
        self.rgb_contrast = colourspace(self.contrast, cv2.COLOR_HSV2RGB_FULL)
        self.bg_image = bg_image
        if self.bg_image is not None:
            h, w, _ = self.original.shape
            bh, bw, _ = self.bg_image.shape
            h, w = min(h, bh), min(w, bw)
            self.original = self.original[0:h, 0:w]
            self.bg_image = self.bg_image[0:h, 0:w]

    @classmethod
    def blur(cls, img):
        """
        Blurs an image by applying a median then gaussian blur.
        :param img: the input image as a numpy array
        :return: the blurred image as a numpy array
        """
        img = cv2.medianBlur(img, 5)
        img = cv2.GaussianBlur(img, (5, 5), 0)
        return img

    @classmethod
    def from_corners(cls, img_array):
        """
        Estimates the background colour of the image using the colour of the corner
        pixels and creates a new BackgroundRemover instance.
        :param img_array: the input image as a numpy array
        :return: BackgroundRemover
        """
        img = cls.blur(img_array)
        corners = np.array([[img[0, 0], img[0, -1], img[-1, 0], img[-1, -1]]])
        corners = cv2.cvtColor(corners, cv2.COLOR_RGB2HSV_FULL)
        var = np.ceil(corners.std(axis=0))
        deviance = abs(np.ma.array(corners).anom(axis=0))
        mask = np.ma.masked_less_equal(deviance, 2).mask
        colour = tuple(np.ma.masked_where(~mask, corners).mean(axis=0).astype(int)[0])
        return cls(colour=colour, original=img_array, variance=var)

    @classmethod
    def from_edges(cls, img_array):
        """
        Estimates the background colour of the image using the colour of the edge
        pixels and creates a new BackgroundRemover instance.
        :param img_array: the input image as a numpy array
        :return: BackgroundRemover
        """
        img = cls.blur(img_array)
        edges = np.vstack(([img[:, 0], img[0], img[-1], img[:, -1]])).reshape(-1, 1, 3)
        edges = cv2.cvtColor(edges, cv2.COLOR_RGB2HSV_FULL)
        var = np.ceil(edges.std(axis=0))
        deviance = np.ma.array(edges).anom(axis=0)
        deviance = deviance / deviance.std(axis=0)
        mask = np.ma.masked_greater(deviance.data, 2).mask
        colour = tuple(np.ma.masked_where(mask, edges).mean(axis=0).astype(int)[0])
        return cls(colour=colour, original=img_array, variance=var)

    def _matches_background(self, colour):
        """
        Returns True if the colour roughly matches the background colour.
        :param colour: an rgb colour
        :return: bool
        """
        colour = colourspace(colour, cv2.COLOR_RGB2HSV_FULL)
        tol = np.array([5, 10, 15])
        lower_bound = (self.colour - self.variance - tol)
        upper_bound = (self.colour + self.variance + tol)
        is_in_range = (lower_bound <= colour).all() and (
                upper_bound >= colour).all()
        return is_in_range

    def _background_contour(self, contour):
        """
        Returns True if the average colour within the contour is roughly the same as
        the background colour.
        :param contour: a numpy array of n (x,y) points in the shape (n,1,2)
        :return: bool
        """
        h, w, _ = self.original.shape
        cm = np.zeros((h, w))
        cm = cv2.drawContours(cm, [contour], 0, 255, -1)
        cm = cm > 0
        cimg = self.blur(self.original.copy())
        avg_colour = cimg[cm].mean(axis=0)
        return self._matches_background(avg_colour)

    def _fill_edge(self, contour):
        """
        Attempts to clean up edges of the contour that are touching edges of the image.
        :param contour: a numpy array of n (x,y) points in the shape (n,1,2)
        :return: the cleaned contour
        """
        h, w, _ = self.original.shape
        sections = [[]]
        for c in contour:
            x, y = c[0]
            if x == 0 or x == w - 1 or y == 0 or y == h - 1:
                sections[-1].append(c)
                sections.append([c])
            else:
                sections[-1].append(c)

        if len(sections) <= 2:
            return contour
        filled_contour = [sections[0]]
        for part in sections[1:-1]:
            cnt = np.array(part)
            if cv2.contourArea(cnt) / len(part) > 5 and self._background_contour(cnt):
                filled_contour.append(part)
        filled_contour.append(sections[-1])
        return np.concatenate(filled_contour)

    def create_mask(self, fill_edge=True, holes=True, erosion=2, use_sobel=False):
        """
        Creates a numpy boolean array, the same size as the original image,
        where False is the background and True is the subject.
        :param fill_edge: whether to attempt to fill/clean edges
        :param holes: whether to allow holes in the subject
        :param erosion: how much to shrink the mask before returning to remove
                        coloured edges
        :return: a mask as a numpy boolean array
        """
        h, w, _ = self.original.shape
        x = math.floor((h * w) ** (1 / 7))
        x = x + 1 if x % 2 == 0 else x
        img = cv2.medianBlur(self.original, x)
        if self.bg_image is None:
            bg_image = np.tile(self.colour, h * w).reshape(img.shape).astype(img.dtype)
            hsv_img = cv2.cvtColor(img, cv2.COLOR_RGB2HSV_FULL)
            hsv_bg = cv2.cvtColor(bg_image, cv2.COLOR_RGB2HSV_FULL)
            diff = cv2.absdiff(hsv_img, hsv_bg)
            diff = diff[..., 0] + (diff[..., 1] * 0.5) + (diff[..., 2] * 0.7)
            diff = ((diff / diff.max()) * 255).astype(img.dtype)
            markers = np.maximum(filters.rank.bottomhat(diff, disk(5)), filters.sobel(diff))
            markers = np.maximum(filters.rank.gradient(diff, disk(5)), markers)
            markers = ndi.label(markers < 10)[0]
            if use_sobel:
                gradient = filters.sobel(diff)
            else:
                gradient = filters.rank.gradient(diff, disk(2))
            labels = watershed(gradient, markers)
            g = future.graph.rag_mean_color(img, labels)
            bg_areas = [v for k, v in g.nodes.items() if
                        self._matches_background(v['mean color'])]
            mask = np.isin(labels, [v['labels'][0] for v in bg_areas])
            contour_mask = np.zeros((h, w)).astype(np.uint8)
            contour_mask = cv2.dilate(contour_mask, None, iterations=erosion)
            contour_mask = cv2.erode(contour_mask, None, iterations=erosion)
            contour_mask[~mask] = 1
        else:
            delta = cv2.absdiff(img, self.bg_image)
            grey_delta = cv2.cvtColor(delta, cv2.COLOR_RGB2GRAY)
            threshold = cv2.adaptiveThreshold(grey_delta, 255,
                                              cv2.ADAPTIVE_THRESH_MEAN_C,
                                              cv2.THRESH_BINARY_INV, 21, 5)
            border = 5
            bordered = cv2.copyMakeBorder(threshold, border, border, border, border,
                                          cv2.BORDER_CONSTANT, 0)
            im2, cont, hier = cv2.findContours(bordered, cv2.RETR_TREE,
                                               cv2.CHAIN_APPROX_SIMPLE)
            contour_stats = list(
                zip([c - border for c in cont], hier.reshape(-1, 4), range(len(cont))))

            parent_contours = []
            child_contours = []
            for parent in [c for c in contour_stats if c[1][3] == -1]:
                p = self._fill_edge(parent[0]) if fill_edge else parent[0]
                if not self._background_contour(p):
                    parent_contours.append(p)
                if holes:
                    child_contours += [child[0] for child in contour_stats
                                       if child[1][3] == parent[2]
                                       and cv2.contourArea(child[0]) > (h * w) * 0.001
                                       and self._background_contour(child[0])]
            contour_mask = np.zeros((h, w)).astype(np.uint8)
            # have to add contours in a loop so they don't cancel each other out
            for p in parent_contours:
                contour_mask = cv2.drawContours(contour_mask, [p], -1, 255, -1)
            for c in child_contours:
                contour_mask = cv2.drawContours(contour_mask, [c], -1, 0, -1)
            contour_mask = cv2.erode(contour_mask, None, iterations=erosion)
        mask_rgba = cv2.cvtColor(contour_mask, cv2.COLOR_GRAY2RGBA)
        mask = mask_rgba[..., 0] == 0
        return mask

    def apply(self, mask):
        """
        Sets the alpha value of the background pixels to 0 and crops to the visible area.
        :param mask: the mask to apply (a numpy boolean array)
        :return: the cropped image with a transparent background, as a numpy array
        """
        rgba_img = cv2.cvtColor(self.original, cv2.COLOR_RGB2RGBA)
        rgba_img[mask] = 0
        pilimage = Image.fromarray(rgba_img)
        bbox = pilimage.getbbox()
        pilimage = pilimage.crop(bbox)
        return np.array(pilimage)
