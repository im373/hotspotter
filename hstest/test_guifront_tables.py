import unittest
from types import SimpleNamespace

from PyQt5 import QtCore
from PyQt5 import QtWidgets

from hscom import params
from hsgui.guiback import MainWindowBackend
from hsgui.guifront import MainWindowFrontend


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


if __name__ == '__main__':
    unittest.main()
