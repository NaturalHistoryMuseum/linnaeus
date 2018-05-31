from unittest.mock import patch

import nose.tools as nosetools
import requests

from linnaeus.factories import MapFactory
from linnaeus.models import ComponentMap, ReferenceMap
from . import helpers


class TestMapFactory:
    def test_factory_returns_class(self):
        nosetools.assert_is_instance(MapFactory.component(), type)
        nosetools.assert_is_instance(MapFactory.reference(), type)

    def test_deserialises_to_correct_type(self):
        nosetools.assert_is_instance(MapFactory.deserialise(helpers.serialised.ref),
                                     ReferenceMap)
        nosetools.assert_is_instance(MapFactory.deserialise(helpers.serialised.comp),
                                     ComponentMap)
        with nosetools.assert_raises(ValueError):
            MapFactory.deserialise(helpers.serialised.invalid)

    def test_deserialises_records(self):
        ref_map = MapFactory.deserialise(helpers.serialised.ref)
        comp_map = MapFactory.deserialise(helpers.serialised.comp)
        nosetools.assert_equal(len(ref_map), 1)
        nosetools.assert_equal(len(comp_map), 1)


class TestReferenceMapFactory:
    def test_from_local(self):
        ref_map = MapFactory.reference().from_image_local(helpers.local.image)
        nosetools.assert_is_instance(ref_map, ReferenceMap)
        nosetools.assert_greater(len(ref_map), 0)

    def test_from_url(self):
        ref_map = MapFactory.reference().from_image_url(helpers.urls.random_image)
        nosetools.assert_is_instance(ref_map, ReferenceMap)
        nosetools.assert_greater(len(ref_map), 0)

    @patch('linnaeus.factories.map.requests.get')
    def test_url_timeout(self, mock_get):
        err = requests.ReadTimeout()
        mock_get.side_effect = [err]
        with nosetools.assert_raises(requests.ReadTimeout):
            ref_map = MapFactory.reference().from_image_url(helpers.urls.random_image)

    def test_from_bytes(self):
        with open(helpers.local.image, 'rb') as f:
            bytestring = f.read()
        ref_map = MapFactory.reference().from_image_bytes(bytestring)
        nosetools.assert_is_instance(ref_map, ReferenceMap)
        nosetools.assert_greater(len(ref_map), 0)


class TestComponentMapFactory:
    def test_from_local_files(self):
        comp_map = MapFactory.component().from_local(files=[helpers.local.image])
        nosetools.assert_is_instance(comp_map, ComponentMap)
        nosetools.assert_greater(len(comp_map), 0)

    def test_from_local_folders(self):
        comp_map = MapFactory.component().from_local(folders=[helpers.local.root])
        nosetools.assert_is_instance(comp_map, ComponentMap)
        nosetools.assert_greater(len(comp_map), 0)

    def test_from_urls(self):
        comp_map = MapFactory.component().from_urls(
            [helpers.urls.random_image, helpers.urls.portal_image])
        nosetools.assert_is_instance(comp_map, ComponentMap)
        nosetools.assert_greater(len(comp_map), 0)

    def test_from_api(self):
        comp_map = MapFactory.component().from_portal(query='red', collectionCode='min')
        nosetools.assert_is_instance(comp_map, ComponentMap)
        nosetools.assert_greater(len(comp_map), 0)
