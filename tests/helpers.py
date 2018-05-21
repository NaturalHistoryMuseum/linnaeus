import os

from linnaeus import ReferenceImage

data_root = os.path.join(os.getcwd(), 'data/')
test_img = data_root + 'img.jpg'
test_url = 'http://www.nhm.ac.uk/services/media-store/asset' \
           '/3f77768aaffdbc58eb5bfa2ef9cafe1f58a773de/contents/preview'


def ref_img():
    return ReferenceImage(path=test_img)
