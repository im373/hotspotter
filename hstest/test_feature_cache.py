import json
import os
import tempfile
import unittest
from unittest import mock

import numpy as np

from hotspotter.feature_compute2 import bigcache_feat_load, bigcache_feat_save
from hotspotter import feature_compute2
from hscom import fileio
from hscom import serialization


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
            paths = feature_compute2._feature_cache_paths(cache_dir, '_test')
            self.assertTrue(all(
                os.path.isfile(component['metadata'])
                and os.path.isfile(component['data'])
                for component in paths.values()
            ))

        for expected, actual in zip(kpts_list, loaded_kpts):
            np.testing.assert_array_equal(actual, expected)
        for expected, actual in zip(desc_list, loaded_desc):
            np.testing.assert_array_equal(actual, expected)

    def test_trusted_legacy_feature_cache_migrates_then_is_not_reloaded(self):
        kpts_list = [
            np.zeros((2, 5), dtype=np.float32),
            np.ones((3, 5), dtype=np.float32),
        ]
        desc_list = [
            np.zeros((2, 128), dtype=np.uint8),
            np.ones((3, 128), dtype=np.uint8),
        ]
        uid = '_legacy-test'
        with tempfile.TemporaryDirectory() as cache_dir:
            fileio.smart_save(
                np.asarray(kpts_list, dtype=object),
                cache_dir, 'kpts_list', uid, '.npy', verbose=False,
            )
            fileio.smart_save(
                np.asarray(desc_list, dtype=object),
                cache_dir, 'desc_list', uid, '.npy', verbose=False,
            )
            with self.assertLogs('hotspotter.feature_compute2', 'INFO') as logs:
                first = bigcache_feat_load(cache_dir, uid, '.npy')
            self.assertTrue(any(
                'Migrated trusted legacy feature cache' in message
                for message in logs.output
            ))

            with mock.patch.object(
                fileio,
                'smart_load',
                side_effect=AssertionError('legacy loader invoked'),
            ):
                second = bigcache_feat_load(cache_dir, uid, '.npy')

        for expected, actual in zip(kpts_list, first[0]):
            np.testing.assert_array_equal(actual, expected)
        for expected, actual in zip(desc_list, first[1]):
            np.testing.assert_array_equal(actual, expected)
        for first_arrays, second_arrays in zip(first, second):
            for expected, actual in zip(first_arrays, second_arrays):
                np.testing.assert_array_equal(actual, expected)

    def test_damaged_current_feature_cache_never_falls_back_to_legacy(self):
        kpts_list = [np.zeros((2, 5), dtype=np.float32)]
        desc_list = [np.zeros((2, 128), dtype=np.uint8)]
        uid = '_damaged-test'
        with tempfile.TemporaryDirectory() as cache_dir:
            bigcache_feat_save(
                cache_dir, uid, '.npy', kpts_list, desc_list
            )
            paths = feature_compute2._feature_cache_paths(cache_dir, uid)
            metadata_path = paths['kpts']['metadata']
            with open(metadata_path, 'r', encoding='utf-8') as file_:
                metadata = json.load(file_)
            metadata['cache_format_version'] = 999
            with open(metadata_path, 'w', encoding='utf-8') as file_:
                json.dump(metadata, file_)

            with mock.patch.object(fileio, 'smart_load') as legacy_loader:
                with self.assertRaisesRegex(
                    serialization.CacheException,
                    'Current cache validation failed',
                ):
                    bigcache_feat_load(cache_dir, uid, '.npy')
            legacy_loader.assert_not_called()


if __name__ == '__main__':
    unittest.main()
