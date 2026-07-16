import ast
import os
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GUIBACK_PATH = os.path.join(REPO_ROOT, 'hsgui', 'guiback.py')


class GuiDependencyDirectionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(GUIBACK_PATH, 'r', encoding='utf-8') as file_:
            cls.tree = ast.parse(file_.read(), filename=GUIBACK_PATH)

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


if __name__ == '__main__':
    unittest.main()
