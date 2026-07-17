import logging
import unittest
from types import SimpleNamespace
from unittest import mock

from PyQt5 import QtCore
from PyQt5 import QtWidgets

from hscom import params
from hsgui.guiback import MainWindowBackend
from hsgui.guifront import (
    GUILoggingHandler,
    MainWindowFrontend,
    add_gui_logging_handler,
)


class GuiFrontTableTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.previous_args = getattr(params, 'args', None)
        params.args = SimpleNamespace(nosteal=True, noshare=True)
        self.backend = MainWindowBackend()
        self.front = MainWindowFrontend(self.backend)

    def tearDown(self):
        self.front.deleteLater()
        params.args = self.previous_args

    def populate_images(self, rows):
        self.front.populate_tbl(
            'gxs',
            ['gx', 'gname', 'nCxs', 'aif'],
            [False, False, False, False],
            [row[0] for row in rows],
            rows,
        )

    def test_views_use_persistent_models_and_sorted_stable_ids(self):
        self.populate_images([
            (20, 'twenty', 10, False),
            (3, 'three', 2, True),
        ])
        model = self.front.table_models['gxs']
        proxy = self.front.table_proxies['gxs']
        view = self.front.table_views['gxs']

        self.assertIsInstance(view, QtWidgets.QTableView)
        self.assertTrue(all(
            isinstance(table_view, QtWidgets.QTableView)
            for table_view in self.front.table_views.values()
        ))
        self.assertIs(view.model(), proxy)
        self.assertIs(proxy.sourceModel(), model)
        self.assertEqual(
            [proxy.index(row, 0).data(QtCore.Qt.UserRole)
             for row in range(proxy.rowCount())],
            [3, 20],
        )
        proxy_index = proxy.index(0, 0)
        source_index = self.front.table_source_index('gxs', proxy_index)
        self.assertEqual(model.record_id_at(source_index.row()), 3)
        self.assertEqual(
            self.front.table_click_record_id('gxs', proxy_index),
            3,
        )

    def test_user_facing_gui_log_handler_defaults_to_info(self):
        handler = GUILoggingHandler(self.front)
        try:
            add_gui_logging_handler(handler)
            self.assertEqual(handler.level, logging.INFO)
        finally:
            logging.getLogger().removeHandler(handler)

    def test_selection_filter_and_model_survive_refresh(self):
        rows = [
            (20, 'twenty', 10, False),
            (3, 'three', 2, True),
        ]
        self.populate_images(rows)
        model = self.front.table_models['gxs']
        proxy = self.front.table_proxies['gxs']
        view = self.front.table_views['gxs']
        model_identity = id(model)
        view.selectRow(1)
        self.assertEqual(self.front.selected_record_ids('gxs'), [20])
        proxy.set_filters({'gname': 'tw*'})

        self.populate_images(list(reversed(rows)))

        self.assertEqual(id(self.front.table_models['gxs']), model_identity)
        self.assertEqual(proxy.rowCount(), 1)
        self.assertEqual(self.front.selected_record_ids('gxs'), [20])
        self.front.clear_table_filters()
        self.assertEqual(proxy.rowCount(), 2)

    def test_checkbox_edit_emits_stable_record_id(self):
        self.populate_images([(20, 'twenty', 10, False)])
        self.front.changeGxSignal.disconnect(self.backend.change_image_property)
        edits = []
        self.front.changeGxSignal.connect(lambda *args: edits.append(args))
        model = self.front.table_models['gxs']
        index = model.index(0, 3)

        changed = model.setData(
            index,
            QtCore.Qt.Checked,
            QtCore.Qt.CheckStateRole,
        )

        self.assertTrue(changed)
        self.assertEqual(edits, [(20, 'aif', True)])

    def test_backend_chip_cell_update_does_not_reset_model(self):
        class FakeHotSpotter(object):
            def get_property_definition(self, key):
                if key == 'rating':
                    return {'datatype': 'int', 'importance': 1}
                return None

        self.backend.hs = FakeHotSpotter()
        self.front.populate_tbl(
            'cxs',
            ['cid', 'name', 'rating'],
            [False, True, True],
            [5],
            [(5, 'alpha', 1)],
        )
        model = self.front.table_models['cxs']
        model_identity = id(model)

        self.backend.chipCellUpdateSignal.emit(5, 'rating', 7)

        self.assertEqual(id(self.front.table_models['cxs']), model_identity)
        self.assertEqual(model.value_at(0, 'rating'), 7)

    def test_nullable_bool_metadata_emits_empty_value(self):
        class FakeHotSpotter(object):
            def get_property_definition(self, key):
                if key == 'reviewed':
                    return {'datatype': 'bool', 'importance': 2}
                return None

        self.backend.hs = FakeHotSpotter()
        self.front.populate_tbl(
            'cxs',
            ['cid', 'reviewed'],
            [False, True],
            [5],
            [(5, True)],
        )
        self.front.changeCidSignal.disconnect(
            self.backend.change_chip_property
        )
        edits = []
        self.front.changeCidSignal.connect(lambda *args: edits.append(args))
        model = self.front.table_models['cxs']
        index = model.index(0, 1)

        changed = model.setData(
            index,
            QtCore.Qt.PartiallyChecked,
            QtCore.Qt.CheckStateRole,
        )

        self.assertTrue(changed)
        self.assertEqual(edits, [(5, 'reviewed', '')])

    def test_chip_metadata_cell_context_helpers_edit_and_clear(self):
        class FakeHotSpotter(object):
            def get_property_definition(self, key):
                if key == 'count':
                    return {'datatype': 'int', 'importance': 2}
                return None

        self.backend.hs = FakeHotSpotter()
        self.front.populate_tbl(
            'cxs',
            ['cid', 'name', 'count'],
            [False, True, True],
            [5],
            [(5, 'alpha', 7)],
        )
        self.front.changeCidSignal.disconnect(
            self.backend.change_chip_property
        )
        edits = []
        self.front.changeCidSignal.connect(lambda *args: edits.append(args))
        view = self.front.table_views['cxs']
        proxy = self.front.table_proxies['cxs']
        source_model = self.front.table_models['cxs']
        source_index = source_model.index(0, 2)
        proxy_index = proxy.mapFromSource(source_index)

        with mock.patch.object(view, 'edit', return_value=True) as edit:
            self.assertTrue(self.front.edit_chip_table_cell(proxy_index))
        edit.assert_called_once_with(proxy_index)

        self.assertTrue(self.front.clear_chip_table_cell(proxy_index))
        self.assertEqual(source_model.value_at(0, 'count'), '')
        self.assertEqual(edits, [(5, 'count', '')])
        self.assertEqual(
            view.contextMenuPolicy(),
            QtCore.Qt.CustomContextMenu,
        )

    def test_chip_cell_context_rejects_builtin_columns(self):
        class FakeHotSpotter(object):
            def get_property_definition(self, key):
                return None

        self.backend.hs = FakeHotSpotter()
        self.front.populate_tbl(
            'cxs',
            ['cid', 'name'],
            [False, True],
            [5],
            [(5, 'alpha')],
        )
        proxy = self.front.table_proxies['cxs']
        source_model = self.front.table_models['cxs']
        proxy_index = proxy.mapFromSource(source_model.index(0, 1))

        self.assertFalse(self.front.clear_chip_table_cell(proxy_index))

    def test_reselect_workflows_hide_and_restore_chip_figure(self):
        context = {
            'gx': 2,
            'cx': 4,
            'roi': [1, 2, 30, 40],
            'theta': 0.25,
        }
        self.backend.get_selected_chip_context = lambda: context

        workflows = [
            ('reselect_roi', 'select_roi', [5, 6, 35, 45]),
            ('reselect_ori', 'select_orientation', 0.75),
        ]
        for workflow_name, selector_name, selected_value in workflows:
            for accepted in (True, False):
                with self.subTest(workflow=workflow_name, accepted=accepted):
                    events = []
                    self.backend.close_chip_figure = (
                        lambda events=events: events.append('close_chip')
                    )
                    self.backend.show_image = (
                        lambda *args, events=events, **kwargs:
                        events.append('show_image')
                    )
                    self.backend.show_chip = (
                        lambda *args, events=events, **kwargs:
                        events.append('restore_chip')
                    )
                    backend_edit = (
                        lambda events=events, **kwargs:
                        events.append('apply_edit')
                    )
                    setattr(self.backend, workflow_name, backend_edit)
                    selector_result = selected_value if accepted else None
                    with mock.patch(
                        'hsgui.guifront.guitools.%s' % selector_name,
                        side_effect=lambda *args, value=selector_result,
                                           events=events, **kwargs:
                        (events.append('select'), value)[1],
                    ):
                        getattr(self.front, workflow_name)()

                    expected = ['close_chip', 'show_image', 'select']
                    expected.append('apply_edit' if accepted else 'restore_chip')
                    self.assertEqual(events, expected)


if __name__ == '__main__':
    unittest.main()
