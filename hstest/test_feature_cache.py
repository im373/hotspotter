import tempfile
import unittest

import numpy as np

from hotspotter.feature_compute2 import bigcache_feat_load, bigcache_feat_save


class FeatureCacheTest(unittest.TestCase):
    def test_variable_length_feature_arrays_round_trip(self):
        kpts_list = [
            np.zeros((2, 5), dtype=np.float32),
            np.ones((3, 5), dtype=np.float32),
        ]
        desc_list = [
            np.zeros((2, 128), dtype=np.uint8),
            np.ones((3, 128), dtype=np.uint8),
        ]

        with tempfile.TemporaryDirectory() as cache_dir:
            bigcache_feat_save(
                cache_dir,
                '_test',
                '.npy',
                kpts_list,
                desc_list,
            )
            loaded_kpts, loaded_desc = bigcache_feat_load(
                cache_dir,
                '_test',
                '.npy',
            )

        for expected, actual in zip(kpts_list, loaded_kpts):
            np.testing.assert_array_equal(actual, expected)
        for expected, actual in zip(desc_list, loaded_desc):
            np.testing.assert_array_equal(actual, expected)


if __name__ == '__main__':
    unittest.main()
