import importlib.util
import os
import unittest

from packaging.requirements import Requirement


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SETUP_PATH = os.path.join(REPO_ROOT, 'setup.py')


def load_setup_module():
    spec = importlib.util.spec_from_file_location(
        'hotspotter_setup_metadata',
        SETUP_PATH,
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SetupMetadataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.setup_module = load_setup_module()

    def test_runtime_requirements_are_valid_and_current(self):
        requirements = self.setup_module.INSTALL_REQUIRES
        parsed_names = {Requirement(item).name.lower() for item in requirements}

        self.assertIn('numpy', parsed_names)
        self.assertIn('pyqt5', parsed_names)
        self.assertIn('pillow', parsed_names)
        self.assertIn('opencv-python', parsed_names)
        self.assertIn('pyflann-ibeis', parsed_names)
        self.assertIn('pyhesaff', parsed_names)
        self.assertNotIn('pil', parsed_names)
        self.assertNotIn('python-qt', parsed_names)

    def test_setuptools_metadata_matches_python3_gui(self):
        metadata = self.setup_module.SETUP_KWARGS

        self.assertEqual(metadata['python_requires'], '>=3.11')
        self.assertIn('hotspotter', metadata['packages'])
        self.assertIn('hsgui', metadata['packages'])
        self.assertNotIn('hstest', metadata['packages'])
        self.assertEqual(
            metadata['entry_points']['console_scripts'],
            ['hotspotter=main:main'],
        )
        self.assertTrue(any('Python :: 3.11' in item
                            for item in metadata['classifiers']))

    def test_setup_has_no_python2_or_pyqt4_build_assumptions(self):
        with open(SETUP_PATH, 'r', encoding='utf-8') as file_:
            source = file_.read()

        self.assertNotIn('PyQt4', source)
        self.assertNotIn('python2.7', source)
        self.assertIn("'PyQt5.sip'", source)


if __name__ == '__main__':
    unittest.main()
