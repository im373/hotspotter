import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

import numpy as np

from hsgui.guiback import MainWindowBackend
from hotspotter import QueryResult as query_result
from hotspotter import chip_properties
from hotspotter import load_data2
from hotspotter import matching_functions
from hotspotter.HotSpotterAPI import HotSpotter


class FakeHotSpotter(object):
    get_property_definition = HotSpotter.get_property_definition
    get_property_definitions = HotSpotter.get_property_definitions
    add_property = HotSpotter.add_property
    update_property_definition = HotSpotter.update_property_definition
    delete_property = HotSpotter.delete_property
    change_property = HotSpotter.change_property
    get_property = HotSpotter.get_property
    cid2_cx = HotSpotter.cid2_cx
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
        self.assertEqual(
            chip_properties.coerce_property_value('1.25', 'float'),
            1.25,
        )
        self.assertIs(chip_properties.coerce_property_value('yes', 'bool'), True)
        self.assertIs(chip_properties.coerce_property_value('0', 'bool'), False)
        for datatype in chip_properties.PROPERTY_DATATYPES:
            with self.subTest(datatype=datatype):
                self.assertEqual(
                    chip_properties.coerce_property_value('', datatype),
                    '',
                )
        with self.assertRaises(ValueError):
            chip_properties.coerce_property_value('sometimes', 'bool')

    def test_numeric_metadata_rejects_out_of_range_values(self):
        self.assertEqual(
            chip_properties.coerce_property_value(
                str(chip_properties.INTEGER_MIN),
                'int',
            ),
            chip_properties.INTEGER_MIN,
        )
        self.assertEqual(
            chip_properties.coerce_property_value(
                str(chip_properties.INTEGER_MAX),
                'int',
            ),
            chip_properties.INTEGER_MAX,
        )
        for value in (
            str(chip_properties.INTEGER_MIN - 1),
            str(chip_properties.INTEGER_MAX + 1),
        ):
            with self.subTest(datatype='int', value=value):
                with self.assertRaisesRegex(ValueError, 'must be between'):
                    chip_properties.coerce_property_value(value, 'int')
        for value in ('1e9999', '-1e9999', 'nan', 'inf', '-inf'):
            with self.subTest(datatype='float', value=value):
                with self.assertRaisesRegex(ValueError, 'must be finite'):
                    chip_properties.coerce_property_value(value, 'float')

    def test_add_typed_property_uses_empty_defaults(self):
        hs = FakeHotSpotter()

        hs.add_property('reviewed', 'bool', 1)
        hs.add_property('weight', 'float', 2)

        self.assertEqual(hs.tables.prop_dict['reviewed'], ['', ''])
        self.assertEqual(hs.tables.prop_dict['weight'], ['', ''])
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

    def test_new_chip_receives_empty_property_default(self):
        hs = FakeHotSpotter()
        hs.add_property('reviewed', 'bool', 1)

        hs.add_chip(0, [1, 2, 3, 4], dochecks=False)

        self.assertEqual(hs.tables.prop_dict['reviewed'],
                         ['', '', ''])

    def test_empty_typed_values_survive_metadata_loading(self):
        with tempfile.TemporaryDirectory() as internal_dir:
            metadata_fpath = os.path.join(
                internal_dir,
                load_data2.CHIP_PROPERTY_METADATA_FNAME,
            )
            with open(metadata_fpath, 'w', encoding='utf-8') as file_:
                json.dump({
                    'version': 1,
                    'properties': {
                        'count': {'datatype': 'int', 'importance': 2},
                        'ratio': {'datatype': 'float', 'importance': 2},
                        'flag': {'datatype': 'bool', 'importance': 2},
                    },
                }, file_)
            prop_dict = {
                'count': ['', '3'],
                'ratio': ['', '1.5'],
                'flag': ['', 'true'],
            }

            definitions = load_data2.load_chip_property_metadata(
                internal_dir,
                prop_dict,
            )

        self.assertEqual(prop_dict['count'], ['', 3])
        self.assertEqual(prop_dict['ratio'], ['', 1.5])
        self.assertEqual(prop_dict['flag'], ['', True])
        self.assertEqual(definitions['count']['datatype'], 'int')
        self.assertEqual(definitions['ratio']['datatype'], 'float')
        self.assertEqual(definitions['flag']['datatype'], 'bool')

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

    def test_backend_rename_and_delete_refresh_only_chip_table(self):
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
        self.assertEqual(back.populate_count, 2)

    def test_chip_metadata_edit_updates_one_cell_without_table_refresh(self):
        hs = FakeHotSpotter()
        hs.add_property('rating', 'int', 1)
        back = MainWindowBackend(hs=hs)
        refreshes = []
        cell_updates = []
        back.populate_chip_table = lambda: refreshes.append('cxs')
        back.populate_tables = lambda **kwargs: refreshes.append(kwargs)
        back.chipCellUpdateSignal.connect(
            lambda *args: cell_updates.append(args)
        )

        back.change_chip_property(1, 'rating', '7')

        self.assertEqual(refreshes, [])
        self.assertEqual(cell_updates, [(1, 'rating', 7)])
        self.assertEqual(hs.tables.prop_dict['rating'][0], 7)

    def test_invalid_numeric_edit_reports_error_and_restores_cell(self):
        hs = FakeHotSpotter()
        hs.add_property('count', 'int', 1)
        hs.add_property('weight', 'float', 1)
        hs.change_property(0, 'count', '7')
        hs.change_property(0, 'weight', '1.5')
        back = MainWindowBackend(hs=hs)
        errors = []
        cell_updates = []
        back.operationFailedSignal.connect(lambda *args: errors.append(args))
        back.chipCellUpdateSignal.connect(
            lambda *args: cell_updates.append(args)
        )

        back.change_chip_property(
            1,
            'count',
            str(chip_properties.INTEGER_MAX + 1),
        )
        back.change_chip_property(1, 'weight', '-1e9999')

        self.assertEqual(len(errors), 2)
        self.assertTrue(all(
            title == 'Invalid Chip Property Value'
            for title, _ in errors
        ))
        self.assertEqual(
            cell_updates,
            [(1, 'count', 7), (1, 'weight', 1.5)],
        )
        self.assertEqual(hs.tables.prop_dict['count'][0], 7)
        self.assertEqual(hs.tables.prop_dict['weight'][0], 1.5)

    def test_chip_name_edit_refreshes_related_tables(self):
        hs = FakeHotSpotter()
        changed_names = []
        hs.change_name = lambda cx, value: changed_names.append((cx, value))
        back = MainWindowBackend(hs=hs)
        refreshes = []
        back.populate_tables = lambda **kwargs: refreshes.append(kwargs)

        back.change_chip_property(1, 'name', 'renamed')

        self.assertEqual(changed_names, [(0, 'renamed')])
        self.assertEqual(refreshes, [{'image': False}])

    def test_roi_and_orientation_edits_refresh_only_chip_table(self):
        hs = FakeHotSpotter()
        edits = []
        hs.change_roi = lambda cx, roi: edits.append(('roi', cx, roi))
        hs.change_theta = lambda cx, theta: edits.append(
            ('orientation', cx, theta)
        )
        hs.save_database = lambda: edits.append(('save',))
        back = MainWindowBackend(hs=hs)
        refreshes = []
        selections = []
        back.populate_chip_table = lambda: refreshes.append('cxs')
        back.populate_tables = lambda **kwargs: refreshes.append(kwargs)
        back.select_gx = lambda gx, cx=None: selections.append((gx, cx))

        back.reselect_roi(cid=1, roi=[1, 2, 8, 9])
        back.reselect_ori(cid=1, theta=0.5)

        self.assertEqual(refreshes, ['cxs', 'cxs'])
        self.assertEqual(selections, [(0, 0), (0, 0)])
        self.assertEqual(
            edits,
            [
                ('roi', 0, [1, 2, 8, 9]),
                ('save',),
                ('orientation', 0, 0.5),
                ('save',),
            ],
        )

    def test_permanent_metadata_filters_neighbor_comparisons(self):
        tables = SimpleNamespace(
            prop_dict={'direction': ['L', 'R', '', 'L']},
            prop_metadata={
                'direction': {'datatype': 'str', 'importance': 2},
            },
            cx2_gx=np.arange(4),
            cx2_nx=np.arange(4),
        )
        hs = SimpleNamespace(tables=tables)
        filt_cfg = SimpleNamespace(
            can_match_sameimg=True,
            can_match_samename=True,
        )
        qreq = SimpleNamespace(
            cfg=SimpleNamespace(
                filt_cfg=filt_cfg,
                nn_cfg=SimpleNamespace(K=3),
            ),
            _data_index=SimpleNamespace(ax2_cx=np.array([1, 2, 3])),
        )
        neighbors = {
            0: (
                np.array([[0, 1, 2]]),
                np.zeros((1, 3), dtype=float),
            ),
        }

        filtered = matching_functions.filter_neighbors(
            hs,
            neighbors,
            {},
            qreq,
        )

        self.assertEqual(filtered[0][1].tolist(), [[False, True, True]])

        tables.prop_dict['direction'][0] = ''
        unfiltered = matching_functions.filter_neighbors(
            hs,
            neighbors,
            {},
            qreq,
        )
        self.assertEqual(unfiltered[0][1].tolist(), [[True, True, True]])

    def test_multiple_permanent_fields_use_wildcards_per_field(self):
        prop_dict = {
            'direction': ['L', 'R', '', 'L'],
            'sex': ['', 'F', 'M', 'M'],
            'note': ['query', 'different', 'different', 'different'],
        }
        definitions = {
            'direction': {'datatype': 'str', 'importance': 2},
            'sex': {'datatype': 'str', 'importance': 2},
            'note': {'datatype': 'str', 'importance': 1},
        }

        query_constraints = chip_properties.permanent_metadata_constraints(
            prop_dict,
            definitions,
            3,
        )
        compatible = [
            chip_properties.metadata_matches_constraints(
                prop_dict,
                cx,
                query_constraints,
            )
            for cx in range(3)
        ]

        self.assertEqual(query_constraints, {'direction': 'L', 'sex': 'M'})
        self.assertEqual(compatible, [True, False, True])

    def test_query_results_hide_incompatible_permanent_metadata(self):
        hs = SimpleNamespace(
            tables=SimpleNamespace(
                prop_dict={'direction': ['L', 'R', '', 'L']},
                prop_metadata={
                    'direction': {'datatype': 'str', 'importance': 2},
                },
            ),
            prefs=SimpleNamespace(
                display_cfg=SimpleNamespace(name_scoring=False, N=10),
            ),
            get_indexed_sample=lambda: np.array([0, 1, 2, 3]),
        )
        result = query_result.QueryResult(0, 'test')
        result.cx2_score = np.array([0.0, 100.0, 50.0, 40.0])

        self.assertEqual(result.topN_cxs(hs, N='all'), [2, 3])

    def test_single_chip_query_indexes_only_compatible_candidates(self):
        hs = SimpleNamespace(
            tables=SimpleNamespace(
                prop_dict={'direction': ['L', 'R', '', 'L']},
                prop_metadata={
                    'direction': {'datatype': 'str', 'importance': 2},
                },
            ),
            prefs=SimpleNamespace(query_cfg=object()),
            qreq=object(),
        )
        prepared_request = object()
        with mock.patch(
            'hotspotter.HotSpotterAPI.mc3.prep_query_request',
            return_value=prepared_request,
        ) as prepare, mock.patch(
            'hotspotter.HotSpotterAPI.mc3.process_query_request',
            return_value={0: 'result'},
        ):
            result = HotSpotter.query_cxs(
                hs,
                0,
                np.array([1, 2, 3]),
            )

        self.assertEqual(result, 'result')
        self.assertEqual(
            prepare.call_args.kwargs['dcxs'].tolist(),
            [2, 3],
        )

    def test_query_with_no_compatible_candidates_skips_matcher(self):
        hs = SimpleNamespace(
            tables=SimpleNamespace(
                cx2_cid=np.array([1, 2]),
                prop_dict={'direction': ['L', 'R']},
                prop_metadata={
                    'direction': {'datatype': 'str', 'importance': 2},
                },
            ),
            prefs=SimpleNamespace(query_cfg=object()),
            qreq=object(),
            get_num_chips=lambda: 2,
        )
        with mock.patch(
            'hotspotter.HotSpotterAPI.mc3.process_query_request'
        ) as process:
            result = HotSpotter.query_cxs(hs, 0, np.array([1]))

        process.assert_not_called()
        self.assertEqual(result.cx2_score.tolist(), [0.0, 0.0])
        self.assertEqual(result.cx2_fm[1].shape, (0, 2))

    def test_permanent_metadata_changes_query_cache_uid(self):
        prop_dict = {'direction': ['L', 'R']}
        definitions = {
            'direction': {'datatype': 'str', 'importance': 2},
        }
        before = chip_properties.permanent_metadata_uid(
            prop_dict,
            definitions,
        )
        prop_dict['direction'][1] = 'L'
        after = chip_properties.permanent_metadata_uid(
            prop_dict,
            definitions,
        )

        self.assertNotEqual(before, after)


if __name__ == '__main__':
    unittest.main()
