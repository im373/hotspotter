import unittest

import numpy as np
from PyQt5 import QtCore
from PyQt5 import QtWidgets

from hsgui.guitablemodel import COLUMN_KEY_ROLE
from hsgui.guitablemodel import DataTableModel
from hsgui.guitablemodel import DataTableProxyModel
from hsgui.guitablemodel import RECORD_ID_ROLE


class DataTableModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.columns = [
            {'key': 'cid', 'header': 'Chip ID'},
            {'key': 'name', 'header': 'Name', 'editable': True},
            {'key': 'enabled', 'header': 'Enabled', 'checkable': True},
        ]
        self.rows = [
            (42, (42, 'alpha', True)),
            (7, (7, 'beta', False)),
        ]
        self.model = DataTableModel(self.columns, self.rows)

    def test_dimensions_data_headers_and_stable_id(self):
        self.assertEqual(self.model.rowCount(), 2)
        self.assertEqual(self.model.columnCount(), 3)
        index = self.model.index(0, 0)
        self.assertEqual(index.data(QtCore.Qt.DisplayRole), 42)
        self.assertEqual(index.data(RECORD_ID_ROLE), 42)
        self.assertEqual(
            self.model.headerData(1, QtCore.Qt.Horizontal),
            'Name',
        )
        self.assertEqual(
            self.model.headerData(1, QtCore.Qt.Horizontal, COLUMN_KEY_ROLE),
            'name',
        )

    def test_numpy_string_scalar_is_renderable_by_qt(self):
        model = DataTableModel(
            [{'key': 'name', 'header': 'Name'}],
            [(2, (np.str_('NMMST_2017_0002_L'),))],
        )
        displayed = model.index(0, 0).data(QtCore.Qt.DisplayRole)
        delegate = QtWidgets.QStyledItemDelegate()

        self.assertIs(type(displayed), str)
        self.assertEqual(displayed, 'NMMST_2017_0002_L')
        self.assertEqual(
            delegate.displayText(displayed, QtCore.QLocale()),
            'NMMST_2017_0002_L',
        )

    def test_flags_and_edit_signal(self):
        name_index = self.model.index(0, 1)
        cid_index = self.model.index(0, 0)
        self.assertTrue(name_index.flags() & QtCore.Qt.ItemIsEditable)
        self.assertFalse(cid_index.flags() & QtCore.Qt.ItemIsEditable)
        edits = []
        self.model.cell_edited.connect(lambda *args: edits.append(args))

        self.assertTrue(self.model.setData(name_index, 'renamed'))

        self.assertEqual(name_index.data(QtCore.Qt.EditRole), 'renamed')
        self.assertEqual(edits, [(42, 'name', 'renamed')])

    def test_checkbox_role_and_edit(self):
        index = self.model.index(1, 2)
        self.assertTrue(index.flags() & QtCore.Qt.ItemIsUserCheckable)
        self.assertEqual(index.data(QtCore.Qt.CheckStateRole), QtCore.Qt.Unchecked)

        self.assertTrue(
            self.model.setData(index, QtCore.Qt.Checked, QtCore.Qt.CheckStateRole)
        )

        self.assertEqual(index.data(QtCore.Qt.EditRole), True)

    def test_set_rows_reuses_model(self):
        self.model.set_rows([(100, (100, 'only', False))])

        self.assertEqual(self.model.rowCount(), 1)
        self.assertEqual(self.model.record_id_at(0), 100)
        self.assertEqual(self.model.record_at(0)['values'][1], 'only')

        self.model.set_rows([])
        self.assertEqual(self.model.rowCount(), 0)


class DataTableProxyModelTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        columns = [
            {'key': 'gname', 'header': 'Image Name'},
            {'key': 'direction', 'header': 'Direction'},
            {'key': 'year', 'header': 'Year'},
        ]
        rows = [
            (20, ('2017_alpha', 'L', 10)),
            (3, ('2017_beta', 'R', 2)),
            (9, ('2018_alpha', 'L', 100)),
            (1, ('other', 'Left', 2017)),
        ]
        self.model = DataTableModel(columns, rows)
        self.proxy = DataTableProxyModel()
        self.proxy.setSourceModel(self.model)

    def visible_ids(self):
        return [
            self.proxy.index(row, 0).data(RECORD_ID_ROLE)
            for row in range(self.proxy.rowCount())
        ]

    def test_exact_wildcard_regex_and_and_filters(self):
        self.proxy.set_filters({'direction': 'L'})
        self.assertEqual(self.visible_ids(), [20, 9])
        self.proxy.set_filters({'gname': '2017_*'})
        self.assertEqual(self.visible_ids(), [20, 3])
        self.proxy.set_filters({'gname': 're:^201[78]_alpha$'})
        self.assertEqual(self.visible_ids(), [20, 9])
        self.proxy.set_filters({'direction': 'L', 'year': '100'})
        self.assertEqual(self.visible_ids(), [9])

    def test_none_filter_and_invalid_regex(self):
        for condition in (None, '', 'None', '  none  '):
            with self.subTest(condition=condition):
                self.proxy.set_filters({'direction': condition})
                self.assertEqual(self.proxy.rowCount(), 4)
        with self.assertRaisesRegex(ValueError, 'gname'):
            self.proxy.set_filters({'gname': 're:['})

    def test_numeric_sort_and_proxy_to_source_identity(self):
        self.proxy.sort(2, QtCore.Qt.AscendingOrder)

        self.assertEqual(self.visible_ids(), [3, 20, 9, 1])
        proxy_index = self.proxy.index(0, 2)
        source_index = self.proxy.mapToSource(proxy_index)
        self.assertEqual(self.model.record_id_at(source_index.row()), 3)

    def test_mixed_query_marker_sorts_before_numeric_ranks(self):
        model = DataTableModel(
            [{'key': 'rank', 'header': 'Rank'}],
            [
                (90, ('!Query',)),
                (1, (10,)),
                (2, (1,)),
            ],
        )
        proxy = DataTableProxyModel()
        proxy.setSourceModel(model)

        proxy.sort(0, QtCore.Qt.AscendingOrder)

        self.assertEqual(
            [proxy.index(row, 0).data(RECORD_ID_ROLE)
             for row in range(proxy.rowCount())],
            [90, 2, 1],
        )

    def test_filter_key_can_be_renamed(self):
        self.proxy.set_filters({'direction': 'L'})

        self.proxy.rename_filter_key('direction', 'gname')

        self.assertEqual(self.proxy.filters(), {'gname': 'L'})
        self.assertEqual(self.proxy.rowCount(), 0)


if __name__ == '__main__':
    unittest.main()
