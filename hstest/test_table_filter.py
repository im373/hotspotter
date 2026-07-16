import unittest

from hsgui.guiback import filter_table_rows


class TableFilterTest(unittest.TestCase):
    def setUp(self):
        self.headers = ['Image', 'Direction', 'Year']
        self.rows = [
            ('2017_alpha', 'L', 2017),
            ('2017_beta', 'R', 2017),
            ('2018_alpha', 'L', 2018),
            ('other', 'Left', 2017),
        ]

    def test_plain_text_is_an_exact_match(self):
        filtered = filter_table_rows(
            self.headers,
            self.rows,
            {'Direction': 'L'},
        )
        self.assertEqual(filtered, [self.rows[0], self.rows[2]])

    def test_wildcard_pattern(self):
        filtered = filter_table_rows(
            self.headers,
            self.rows,
            {'Image': '2017_*'},
        )
        self.assertEqual(filtered, [self.rows[0], self.rows[1]])

    def test_raw_regular_expression(self):
        filtered = filter_table_rows(
            self.headers,
            self.rows,
            {'Image': 're:^201[78]_alpha$'},
        )
        self.assertEqual(filtered, [self.rows[0], self.rows[2]])

    def test_columns_are_combined_with_and(self):
        filtered = filter_table_rows(
            self.headers,
            self.rows,
            {'Direction': 'L', 'Year': '2018'},
        )
        self.assertEqual(filtered, [self.rows[2]])

    def test_none_values_disable_filtering(self):
        for condition in (None, '', 'None', '  none  '):
            with self.subTest(condition=condition):
                filtered = filter_table_rows(
                    self.headers,
                    self.rows,
                    {'Direction': condition},
                )
                self.assertEqual(filtered, self.rows)

    def test_invalid_regular_expression(self):
        with self.assertRaisesRegex(ValueError, 'Image'):
            filter_table_rows(
                self.headers,
                self.rows,
                {'Image': 're:['},
            )


if __name__ == '__main__':
    unittest.main()
