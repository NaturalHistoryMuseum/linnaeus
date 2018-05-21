from linnaeus import ReferenceImage
from . import helpers
import nose.tools
import os


class TestReferenceImage(object):
    def test_load_from_path(self):
        ref = ReferenceImage(path=helpers.test_img)
        nose.tools.assert_is_not_none(ref.img)

    def test_load_from_bytes(self):
        with open(helpers.test_img, 'rb') as f:
            b = f.read()
        ref = ReferenceImage(data=b)
        nose.tools.assert_is_not_none(ref.img)

    def test_compare_load_methods(self):
        from_path = ReferenceImage(path=helpers.test_img)
        with open(helpers.test_img, 'rb') as f:
            b = f.read()
        from_bytes = ReferenceImage(data=b)
        nose.tools.eq_(from_path.img, from_bytes.img)
