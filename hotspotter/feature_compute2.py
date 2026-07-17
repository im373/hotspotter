# HotSpotter port notes:
# Modernized core HotSpotter logic for Python 3 and NumPy 2 compatibility.
# Adjusted chip, feature, query, and table handling for current dependencies.

''' Computes feature representations '''

import logging
import os
from hscom.dev_utils import make_reloader
from hscom.profiling import profile

logger = logging.getLogger(__name__)
rrr = make_reloader(__name__, '[fc2]')
# scientific
import numpy as np
# python
from os.path import join
# hotspotter
from hscom import helpers as util
from hscom import array_utils
from hscom import progress
from hscom import serialization
from hscom import params
from hscom import fileio as io
from hscom.Parallelize import parallel_compute
from . import extern_feat


def whiten_features(desc_list):
    from . import algos
    logger.debug('[fc2] * Whitening features')
    ax2_desc = np.vstack(desc_list)
    ax2_desc_white = algos.scale_to_byte(algos.whiten(ax2_desc))
    index = 0
    offset = 0
    for cx in range(len(desc_list)):
        old_desc = desc_list[cx]
        logger.debug("[fc2] * %s", util.info(old_desc, 'old_desc'))
        offset = len(old_desc)
        new_desc = ax2_desc_white[index:(index + offset)]
        desc_list[cx] = new_desc
        index += offset


# =======================================
# Main Script
# =======================================
_FEATURE_CACHE_COMPONENT_UIDS = {
    'kpts': 'feature-bigcache-kpts',
    'desc': 'feature-bigcache-desc',
    'lengths': 'feature-bigcache-lengths',
}


def _feature_cache_key(uid):
    """Use the complete legacy UID as the versioned cache input identity."""
    return np.frombuffer(uid.encode('utf-8'), dtype=np.uint8)


def _pack_feature_lists(kpts_list, desc_list):
    if len(kpts_list) != len(desc_list):
        raise ValueError('Keypoint and descriptor cache lengths differ')
    if not kpts_list:
        return (
            np.empty((0, 0), dtype=np.float32),
            np.empty((0, 0), dtype=np.uint8),
            np.empty(0, dtype=np.int64),
        )
    kpts_arrays = [np.asarray(kpts) for kpts in kpts_list]
    desc_arrays = [np.asarray(desc) for desc in desc_list]
    for index, (kpts, desc) in enumerate(zip(kpts_arrays, desc_arrays)):
        if kpts.ndim != 2 or desc.ndim != 2:
            raise ValueError('Feature cache item %d is not two-dimensional' % index)
        if len(kpts) != len(desc):
            raise ValueError(
                'Feature cache item %d has mismatched row counts' % index
            )
        if kpts.dtype.hasobject or desc.dtype.hasobject:
            raise ValueError('Feature cache contains nested object data')
    kpts_shapes = {(array.shape[1], array.dtype.str) for array in kpts_arrays}
    desc_shapes = {(array.shape[1], array.dtype.str) for array in desc_arrays}
    if len(kpts_shapes) != 1 or len(desc_shapes) != 1:
        raise ValueError('Feature cache column counts or dtypes differ')
    lengths = np.asarray([len(array) for array in kpts_arrays], dtype=np.int64)
    return (
        np.concatenate(kpts_arrays, axis=0),
        np.concatenate(desc_arrays, axis=0),
        lengths,
    )


def _unpack_feature_lists(kpts, desc, lengths):
    kpts = np.asarray(kpts)
    desc = np.asarray(desc)
    lengths = np.asarray(lengths)
    if kpts.ndim != 2 or desc.ndim != 2 or lengths.ndim != 1:
        raise ValueError('Versioned feature cache has invalid dimensions')
    if lengths.dtype.kind not in 'iu' or np.any(lengths < 0):
        raise ValueError('Versioned feature cache has invalid row lengths')
    if int(lengths.sum()) != len(kpts) or len(kpts) != len(desc):
        raise ValueError('Versioned feature cache row lengths do not match data')
    offsets = np.concatenate(([0], np.cumsum(lengths, dtype=np.int64)))
    kpts_list = [kpts[start:stop].copy()
                 for start, stop in zip(offsets[:-1], offsets[1:])]
    desc_list = [desc[start:stop].copy()
                 for start, stop in zip(offsets[:-1], offsets[1:])]
    return kpts_list, desc_list


def _feature_cache_paths(cache_dir, uid):
    key = _feature_cache_key(uid)
    return {
        name: serialization.get_cache_paths(
            key, uid=component_uid, cache_dir=cache_dir
        )
        for name, component_uid in _FEATURE_CACHE_COMPONENT_UIDS.items()
    }


@profile
def bigcache_feat_save(cache_dir, uid, ext, kpts_list, desc_list):
    """Save ragged features as validated, pickle-free cache_v2 components."""
    logger.debug('[fc2] Caching desc_list and kpts_list in cache_v2')
    key = _feature_cache_key(uid)
    kpts, desc, lengths = _pack_feature_lists(kpts_list, desc_list)
    for name, data in (
        ('kpts', kpts), ('desc', desc), ('lengths', lengths)
    ):
        serialization.save_cache_npz(
            key,
            data,
            uid=_FEATURE_CACHE_COMPONENT_UIDS[name],
            cache_dir=cache_dir,
        )


@profile
def bigcache_feat_load(cache_dir, uid, ext):
    """Load cache_v2 directly, or migrate a trusted legacy feature cache."""
    key = _feature_cache_key(uid)
    paths = _feature_cache_paths(cache_dir, uid)
    current_exists = {
        name: os.path.exists(component_paths['current_dir'])
        for name, component_paths in paths.items()
    }
    if any(current_exists.values()):
        if not all(current_exists.values()):
            missing = sorted(
                name for name, exists_ in current_exists.items() if not exists_
            )
            raise serialization.CacheException(
                'Current feature cache is incomplete; missing %r' % missing
            )
        try:
            components = {
                name: serialization.load_cache_npz(
                    key,
                    uid=component_uid,
                    cache_dir=cache_dir,
                    allow_legacy=False,
                )
                for name, component_uid in _FEATURE_CACHE_COMPONENT_UIDS.items()
            }
            loaded = _unpack_feature_lists(
                components['kpts'], components['desc'], components['lengths']
            )
        except serialization.CacheException:
            raise
        except Exception as ex:
            raise serialization.CacheException(
                'Current feature cache validation failed: %s' % ex
            ) from ex
        logger.info('[fc2] Loaded feature cache_v2 directly')
        return loaded

    # These object-array files are trusted local HotSpotter caches. Validate
    # and immediately convert them; never write new object-array caches.
    kpts_array = io.smart_load(
        cache_dir, 'kpts_list', uid, ext, can_fail=True
    )
    desc_array = io.smart_load(
        cache_dir, 'desc_list', uid, ext, can_fail=True
    )
    if desc_array is None or kpts_array is None:
        return None
    kpts_list = kpts_array.tolist()
    desc_list = desc_array.tolist()
    _pack_feature_lists(kpts_list, desc_list)
    bigcache_feat_save(cache_dir, uid, ext, kpts_list, desc_list)
    logger.info('[fc2] Migrated trusted legacy feature cache to cache_v2')
    return kpts_list, desc_list


@profile
def sequential_feat_load(feat_cfg, feat_fpath_list):
    kpts_list = []
    desc_list = []
    # Debug loading (seems to use lots of memory)
    logger.debug('')
    try:
        nFeats = len(feat_fpath_list)
        prog_label = '[fc2] Loading feature: '
        mark_progress, end_progress = progress.progress_func(nFeats, prog_label)
        for count, feat_path in enumerate(feat_fpath_list):
            try:
                archive = serialization.load_npz_archive(
                    feat_path,
                    expected_keys=('arr_0', 'arr_1'),
                )
            except IOError:
                logger.debug('')
                util.checkpath(feat_path, verbose=True)
                logger.exception('IOError on feat_path=%r', feat_path)
                raise
            kpts = archive['arr_0']
            desc = archive['arr_1']
            kpts_list.append(kpts)
            desc_list.append(desc)
            mark_progress(count)
        end_progress()
        logger.debug('[fc2] Finished load of individual kpts and desc')
    except MemoryError:
        logger.exception('[fc2] Out of memory while loading features')
        logger.error('[fc2] Trying to read: %r', feat_path)
        logger.debug('[fc2] len(kpts_list) = %d', len(kpts_list))
        logger.debug('[fc2] len(desc_list) = %d', len(desc_list))
        raise
    if feat_cfg.whiten:
        desc_list = whiten_features(desc_list)
    return kpts_list, desc_list


# Maps a preference string into a function
feat_type2_precompute = {
    'hesaff+sift': extern_feat.precompute_hesaff,
}


@profile
def _load_features_individualy(hs, cx_list):
    use_cache = not params.args.nocache_feats
    feat_cfg = hs.prefs.feat_cfg
    feat_dir = hs.dirs.feat_dir
    feat_uid = feat_cfg.get_uid()
    logger.debug("[fc2]  Loading %s individually", feat_uid)
    # Build feature paths
    rchip_fpath_list = [hs.cpaths.cx2_rchip_path[cx] for cx in iter(cx_list)]
    cid_list = hs.tables.cx2_cid[cx_list]
    feat_fname_fmt = ''.join(('cid%d', feat_uid, '.npz'))
    feat_fpath_fmt = join(feat_dir, feat_fname_fmt)
    feat_fpath_list = [feat_fpath_fmt % cid for cid in cid_list]
    #feat_fname_list = [feat_fname_fmt % cid for cid in cid_list]
    # Compute features in parallel, saving them to disk
    kwargs_list = [feat_cfg.get_dict_args()] * len(rchip_fpath_list)
    pfc_kwargs = {
        'func': feat_type2_precompute[feat_cfg.feat_type],
        'arg_list': [rchip_fpath_list, feat_fpath_list, kwargs_list],
        'num_procs': params.args.num_procs,
        'lazy': use_cache,
    }
    parallel_compute(**pfc_kwargs)
    # Load precomputed features sequentially
    kpts_list, desc_list = sequential_feat_load(feat_cfg, feat_fpath_list)
    return kpts_list, desc_list


@profile
def _load_features_bigcache(hs, cx_list):
    # args for smart load/save
    feat_cfg = hs.prefs.feat_cfg
    feat_uid = feat_cfg.get_uid()
    cache_dir  = hs.dirs.cache_dir
    sample_uid = serialization.hashstr_arr(cx_list, 'cids')
    bigcache_uid = '_'.join((feat_uid, sample_uid))
    ext = '.npy'
    loaded = bigcache_feat_load(cache_dir, bigcache_uid, ext)
    if loaded is not None:  # Cache Hit
        kpts_list, desc_list = loaded
    else:  # Cache Miss
        kpts_list, desc_list = _load_features_individualy(hs, cx_list)
        # Cache all the features
        bigcache_feat_save(cache_dir, bigcache_uid, ext, kpts_list, desc_list)
    return kpts_list, desc_list


@profile
@util.indent_decor('[fc2]')
def load_features(hs, cx_list=None, **kwargs):
    # TODO: There needs to be a fast way to ensure that everything is
    # already loaded. Same for cc2.
    logger.debug('=============================')
    logger.debug('[fc2] Precomputing and loading features: %r', hs.get_db_name())
    #----------------
    # COMPUTE SETUP
    #----------------
    use_cache = not params.args.nocache_feats
    use_big_cache = use_cache and cx_list is None
    feat_cfg = hs.prefs.feat_cfg
    feat_uid = feat_cfg.get_uid()
    if hs.feats.feat_uid != '' and hs.feats.feat_uid != feat_uid:
        logger.info('[fc2] Feature config changed; unloading cached feature information')
        logger.debug('[fc2] Disagreement: OLD_feat_uid = %r', hs.feats.feat_uid)
        logger.debug('[fc2] Disagreement: NEW_feat_uid = %r', feat_uid)
        hs.unload_all()
        hs.load_chips(cx_list=cx_list)
    logger.debug('[fc2] feat_uid = %r', feat_uid)
    # Get the list of chip features to load
    cx_list = hs.get_valid_cxs() if cx_list is None else cx_list
    if not np.iterable(cx_list):
        cx_list = [cx_list]
    logger.debug('[fc2] len(cx_list) = %r', len(cx_list))
    if len(cx_list) == 0:
        return  # HACK
    cx_list = np.array(cx_list)  # HACK
    if use_big_cache:  # use only if all descriptors requested
        kpts_list, desc_list = _load_features_bigcache(hs, cx_list)
    else:
        kpts_list, desc_list = _load_features_individualy(hs, cx_list)
    # Extend the datastructure if needed
    list_size = max(cx_list) + 1
    array_utils.ensure_list_size(hs.feats.cx2_kpts, list_size)
    array_utils.ensure_list_size(hs.feats.cx2_desc, list_size)
    # Copy the values into the ChipPaths object
    for lx, cx in enumerate(cx_list):
        hs.feats.cx2_kpts[cx] = kpts_list[lx]
    for lx, cx in enumerate(cx_list):
        hs.feats.cx2_desc[cx] = desc_list[lx]
    hs.feats.feat_uid = feat_uid
    logger.debug('[fc2]=============================')


def clear_feature_cache(hs):
    feat_cfg = hs.prefs.feat_cfg
    feat_dir = hs.dirs.feat_dir
    cache_dir = hs.dirs.cache_dir
    feat_uid = feat_cfg.get_uid()
    logger.info('[fc2] clearing feature cache: %r', feat_dir)
    util.remove_files_in_dir(feat_dir, '*' + feat_uid + '*', verbose=True, dryrun=False)
    util.remove_files_in_dir(cache_dir, '*' + feat_uid + '*', verbose=True, dryrun=False)
    pass
