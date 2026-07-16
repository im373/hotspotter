import ast
import os
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIBACK_PATH = os.path.join(REPO_ROOT, 'hsgui', 'guiback.py')
TABLE_MODEL_PATH = os.path.join(REPO_ROOT, 'hsgui', 'guitablemodel.py')


class GuiDependencyDirectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(GUIBACK_PATH, 'r', encoding='utf-8') as file_:
            cls.tree = ast.parse(file_.read(), filename=GUIBACK_PATH)
        with open(TABLE_MODEL_PATH, 'r', encoding='utf-8') as file_:
            cls.table_model_tree = ast.parse(
                file_.read(),
                filename=TABLE_MODEL_PATH,
            )

    def test_backend_does_not_import_frontend(self):
        imported_names = []
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                imported_names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported_names.extend(alias.name for alias in node.names)
        self.assertNotIn('guifront', imported_names)
        self.assertNotIn('hsgui.guifront', imported_names)

    def test_backend_does_not_access_front_attribute(self):
        front_attributes = [
            node
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Attribute) and node.attr == 'front'
        ]
        self.assertEqual(front_attributes, [])

    def test_backend_has_no_display_header_mapping(self):
        attribute_names = {
            node.attr
            for node in ast.walk(self.tree)
            if isinstance(node, ast.Attribute)
        }
        self.assertNotIn('fancy_headers', attribute_names)
        self.assertNotIn('reverse_fancy', attribute_names)

    def test_table_model_does_not_import_or_access_backend(self):
        imported_names = []
        backend_attributes = []
        for node in ast.walk(self.table_model_tree):
            if isinstance(node, ast.Import):
                imported_names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported_names.append(node.module)
            elif isinstance(node, ast.Attribute) and node.attr == 'backend':
                backend_attributes.append(node)
        self.assertNotIn('hsgui.guiback', imported_names)
        self.assertNotIn('guiback', imported_names)
        self.assertEqual(backend_attributes, [])


if __name__ == '__main__':
    unittest.main()
