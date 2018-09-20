from PIL import ExifTags, Image


def apply_orientation(img: Image):
    """
    Applies the orientation defined in the Image's EXIF tags (if there are any).
    :param img: a PIL image object
    :return: a PIL image object in the correct orientation
    """
    try:
        exif = img._getexif()
    except AttributeError:
        return img
    orient = {ExifTags.TAGS.get(k, None): v for k, v in exif.items()}.get('Orientation',
                                                                          0)

    rotate_lookup = {
        1: lambda x: x,
        2: lambda x: x.transpose(Image.FLIP_LEFT_RIGHT),
        3: lambda x: x.transpose(Image.ROTATE_180),
        4: lambda x: x.transpose(Image.FLIP_TOP_BOTTOM),
        5: lambda x: x.transpose(Image.FLIP_TOP_BOTTOM).transpose(Image.ROTATE_90),
        6: lambda x: x.transpose(Image.ROTATE_270),
        7: lambda x: x.transpose(Image.FLIP_LEFT_RIGHT).transpose(Image.ROTATE_90),
        8: lambda x: x.transpose(Image.ROTATE_90)
        }

    return rotate_lookup.get(orient, rotate_lookup[1])(img)