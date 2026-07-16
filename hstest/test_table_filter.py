import unittest

from PyQt5 import QtWidgets

from hsgui.guitablemodel import DataTableModel
from hsgui.guitablemodel import DataTableProxyModel


class TableFilterTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.headers = ['gname', 'direction', 'year']
        self.rows = [
            ('2017_alpha', 'L', 2017),
            ('2017_beta', 'R', 2017),
            ('2018_alpha', 'L', 2018),
            ('other', 'Left', 2017),
        ]

    def filtered_rows(self, conditions):
        columns = [
            {'key': header, 'header': header}
            for header in self.headers
        ]
        model = DataTableModel(
            columns,
            list(enumerate(self.rows)),
        )
        proxy = DataTableProxyModel()
        proxy.setSourceModel(model)
        proxy.set_filters(conditions)
        return [
            model.record_at(proxy.mapToSource(proxy.index(row, 0)).row())['values']
            for row in range(proxy.rowCount())
        ]

    def test_plain_text_is_an_exact_match(self):
        filtered = self.filtered_rows({'direction': 'L'})
        self.assertEqual(filtered, [self.rows[0], self.rows[2]])

    def test_wildcard_pattern(self):
        filtered = self.filtered_rows({'gname': '2017_*'})
        self.assertEqual(filtered, [self.rows[0], self.rows[1]])

    def test_raw_regular_expression(self):
        filtered = self.filtered_rows({'gname': 're:^201[78]_alpha$'})
        self.assertEqual(filtered, [self.rows[0], self.rows[2]])

    def test_columns_are_combined_with_and(self):
        filtered = self.filtered_rows({'direction': 'L', 'year': '2018'})
        self.assertEqual(filtered, [self.rows[2]])

    def test_none_values_disable_filtering(self):
        for condition in (None, '', 'None', '  none  '):
            with self.subTest(condition=condition):
                filtered = self.filtered_rows({'direction': condition})
                self.assertEqual(filtered, self.rows)

    def test_invalid_regular_expression(self):
        with self.assertRaisesRegex(ValueError, 'gname'):
            self.filtered_rows({'gname': 're:['})

    def test_clear_filters_restores_all_rows(self):
        columns = [
            {'key': header, 'header': header}
            for header in self.headers
        ]
        model = DataTableModel(columns, list(enumerate(self.rows)))
        proxy = DataTableProxyModel()
        proxy.setSourceModel(model)
        proxy.set_filters({'direction': 'L'})
        self.assertEqual(proxy.rowCount(), 2)

        proxy.clear_filters()

        self.assertEqual(proxy.filters(), {})
        self.assertEqual(proxy.rowCount(), 4)


if __name__ == '__main__':
    unittest.main()
