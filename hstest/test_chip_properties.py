import json
import os
import tempfile
import unittest
from types import SimpleNamespace

import numpy as np

from hsgui.guiback import MainWindowBackend
from hotspotter import chip_properties
from hotspotter import load_data2
from hotspotter.HotSpotterAPI import HotSpotter


class FakeHotSpotter(object):
    get_property_definition = HotSpotter.get_property_definition
    get_property_definitions = HotSpotter.get_property_definitions
    add_property = HotSpotter.add_property
    update_property_definition = HotSpotter.update_property_definition
    delete_property = HotSpotter.delete_property
    change_property = HotSpotter.change_property
    add_chip = HotSpotter.add_chip

    def __init__(self):
        self.tables = SimpleNamespace(
            prop_dict={'quality': ['1', '2']},
            prop_metadata={
                'quality': {'datatype': 'str', 'importance': 0},
            },
            cx2_cid=np.array([1, 2]),
            cx2_nx=np.array([0, 0]),
            cx2_gx=np.array([0, 0]),
            cx2_roi=np.array([[0, 0, 10, 10], [0, 0, 10, 10]]),
            cx2_theta=np.array([0.0, 0.0]),
        )

    def get_num_chips(self):
        return len(self.tables.cx2_cid)


class ChipPropertyTest(unittest.TestCase):
    def test_value_coercion(self):
        self.assertEqual(chip_properties.coerce_property_value('12', 'int'), 12)
        self.assertIs(chip_properties.coerce_property_value('yes', 'bool'), True)
        self.assertIs(chip_properties.coerce_property_value('0', 'bool'), False)
        with self.assertRaises(ValueError):
            chip_properties.coerce_property_value('sometimes', 'bool')

    def test_add_typed_property_uses_typed_defaults(self):
        hs = FakeHotSpotter()

        hs.add_property('reviewed', 'bool', 1)

        self.assertEqual(hs.tables.prop_dict['reviewed'], [False, False])
        self.assertEqual(
            hs.tables.prop_metadata['reviewed'],
            {'datatype': 'bool', 'importance': 1},
        )

    def test_update_can_rename_and_convert_property(self):
        hs = FakeHotSpotter()

        new_key = hs.update_property_definition('quality', 'rating', 'int', 2)

        self.assertEqual(new_key, 'rating')
        self.assertNotIn('quality', hs.tables.prop_dict)
        self.assertEqual(hs.tables.prop_dict['rating'], [1, 2])
        self.assertEqual(
            hs.tables.prop_metadata['rating'],
            {'datatype': 'int', 'importance': 2},
        )

    def test_failed_type_conversion_does_not_modify_property(self):
        hs = FakeHotSpotter()
        hs.tables.prop_dict['quality'][1] = 'not-an-int'

        with self.assertRaises(ValueError):
            hs.update_property_definition('quality', 'rating', 'int', 1)

        self.assertEqual(hs.tables.prop_dict['quality'], ['1', 'not-an-int'])
        self.assertNotIn('rating', hs.tables.prop_dict)

    def test_change_property_uses_declared_datatype(self):
        hs = FakeHotSpotter()
        hs.add_property('reviewed', 'bool', 1)

        hs.change_property(0, 'reviewed', 'true')

        self.assertIs(hs.tables.prop_dict['reviewed'][0], True)

    def test_new_chip_receives_typed_property_default(self):
        hs = FakeHotSpotter()
        hs.add_property('reviewed', 'bool', 1)

        hs.add_chip(0, [1, 2, 3, 4], dochecks=False)

        self.assertEqual(hs.tables.prop_dict['reviewed'],
                         [False, False, False])

    def test_delete_removes_values_and_definition(self):
        hs = FakeHotSpotter()

        hs.delete_property('quality')

        self.assertNotIn('quality', hs.tables.prop_dict)
        self.assertNotIn('quality', hs.tables.prop_metadata)

    def test_reserved_property_name_is_rejected(self):
        hs = FakeHotSpotter()
        with self.assertRaisesRegex(ValueError, 'reserved'):
            hs.add_property('Chip ID', 'str', 0)

    def test_metadata_sidecar_round_trip(self):
        with tempfile.TemporaryDirectory() as internal_dir:
            hs = SimpleNamespace(
                dirs=SimpleNamespace(internal_dir=internal_dir),
                tables=SimpleNamespace(
                    prop_dict={'reviewed': [True, False]},
                    prop_metadata={
                        'reviewed': {'datatype': 'bool', 'importance': 2},
                    },
                ),
            )

            load_data2.write_chip_property_metadata(hs)
            metadata_fpath = os.path.join(
                internal_dir,
                load_data2.CHIP_PROPERTY_METADATA_FNAME,
            )
            with open(metadata_fpath, 'r', encoding='utf-8') as file_:
                payload = json.load(file_)
            prop_dict = {'reviewed': ['True', 'False']}
            definitions = load_data2.load_chip_property_metadata(
                internal_dir,
                prop_dict,
            )

        self.assertEqual(payload['version'], 1)
        self.assertEqual(
            definitions['reviewed'],
            {'datatype': 'bool', 'importance': 2},
        )
        self.assertEqual(prop_dict['reviewed'], [True, False])

    def test_missing_sidecar_defaults_existing_properties_to_strings(self):
        with tempfile.TemporaryDirectory() as internal_dir:
            prop_dict = {'legacy': ['1', 'True']}
            definitions = load_data2.load_chip_property_metadata(
                internal_dir,
                prop_dict,
            )

        self.assertEqual(
            definitions['legacy'],
            {'datatype': 'str', 'importance': 0},
        )
        self.assertEqual(prop_dict['legacy'], ['1', 'True'])

    def test_invalid_typed_value_falls_back_to_legacy_string(self):
        with tempfile.TemporaryDirectory() as internal_dir:
            metadata_fpath = os.path.join(
                internal_dir,
                load_data2.CHIP_PROPERTY_METADATA_FNAME,
            )
            with open(metadata_fpath, 'w', encoding='utf-8') as file_:
                json.dump({
                    'version': 1,
                    'properties': {
                        'quality': {'datatype': 'int', 'importance': 1},
                    },
                }, file_)
            prop_dict = {'quality': ['1', 'not-an-int']}

            definitions = load_data2.load_chip_property_metadata(
                internal_dir,
                prop_dict,
            )

        self.assertEqual(
            definitions['quality'],
            {'datatype': 'str', 'importance': 0},
        )
        self.assertEqual(prop_dict['quality'], ['1', 'not-an-int'])

    def test_backend_rename_and_delete_refresh_tables(self):
        class FakeBackend(object):
            def __init__(self):
                self.hs = FakeHotSpotter()
                self.populate_count = 0

            def populate_chip_table(self):
                self.populate_count += 1

            def populate_result_table(self):
                self.populate_count += 1

        back = FakeBackend()

        MainWindowBackend.update_chip_property_definition(
            back,
            'quality',
            {'name': 'rating', 'datatype': 'int', 'importance': 1},
        )
        MainWindowBackend.delete_chip_property(back, 'rating')

        self.assertNotIn('rating', back.hs.tables.prop_dict)
        self.assertEqual(back.populate_count, 4)


if __name__ == '__main__':
    unittest.main()
