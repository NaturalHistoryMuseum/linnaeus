from linnaeus import Map, MapRecord
from . import helpers
import nose.tools
import os


class TestMaps(object):
    def test_save_ref_map_as_csv(self):
        csv_path = 'outputs/ref_map.csv'
        if os.path.exists(csv_path):
            os.remove(csv_path)
        ref = helpers.ref_img()
        ref_map = ref.get_map()
        ref_map.save_to_csv(csv_path)
        nose.tools.assert_true(os.path.exists(csv_path))


