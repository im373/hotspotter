import sys
import unittest
from unittest import mock

import numpy as np

from hstpl.extern_feat import pyhesaff as wrapper


class PyHesaffWrapperTest(unittest.TestCase):
    def setUp(self):
        self.img = np.zeros((8, 8), dtype=np.uint8)
        self.kpts = np.zeros((2, 5), dtype=np.float32)
        self.desc = np.zeros((2, 128), dtype=np.uint8)

    def test_wrapper_options_are_not_forwarded_to_detector(self):
        backend = mock.Mock()
        backend.detect_feats_in_image.return_value = (self.kpts, self.desc)

        with mock.patch.dict(sys.modules, {'pyhesaff': backend}), mock.patch.object(
                wrapper, '_load_detect_image', return_value=self.img):
            result = wrapper.detect_kpts(
                'chip.png', use_adaptive_scale=False,
                scale_min=0, scale_max=9001)

        backend.detect_feats_in_image.assert_called_once_with(
            self.img, scale_min=0, scale_max=9001)
        backend.adapt_scale.assert_not_called()
        self.assertIs(result[0], self.kpts)
        self.assertIs(result[1], self.desc)

    def test_adaptive_scale_is_applied_after_detection(self):
        adapted_kpts = np.ones((2, 5), dtype=np.float32)
        adapted_desc = np.ones((2, 128), dtype=np.uint8)
        backend = mock.Mock()
        backend.detect_feats_in_image.return_value = (self.kpts, self.desc)
        backend.adapt_scale.return_value = (adapted_kpts, adapted_desc)

        with mock.patch.dict(sys.modules, {'pyhesaff': backend}), mock.patch.object(
                wrapper, '_load_detect_image', return_value=self.img):
            result = wrapper.detect_kpts(
                'chip.png', use_adaptive_scale=True,
                scale_min=0, scale_max=9001)

        backend.detect_feats_in_image.assert_called_once_with(
            self.img, scale_min=0, scale_max=9001)
        backend.adapt_scale.assert_called_once_with('chip.png', self.kpts)
        self.assertIs(result[0], adapted_kpts)
        self.assertIs(result[1], adapted_desc)


if __name__ == '__main__':
    unittest.main()
