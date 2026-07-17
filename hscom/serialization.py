"""Safe text, NumPy archive, pickle, hashing, and cache helpers."""

from collections import OrderedDict
import codecs
import hashlib
import json
import logging
import os
import pickle
import tempfile

import numpy as np


logger = logging.getLogger(__name__)

VERY_VERBOSE = False
PRINT_WRITES = False

CACHE_FORMAT_VERSION = 2
CACHE_NAMESPACE = 'cache_v%d' % CACHE_FORMAT_VERSION
LEGACY_HASH_FORMAT_VERSION = 1
HASH_FORMAT_VERSION = 2
HASH_ALGORITHM = 'sha256-canonical-numpy-v2'


def sanatize_fname2(fname):
    return fname.replace(' ', '_')


def sanatize_fname(fname):
    ext = '.pkl'
    if fname.rfind(ext) != max(len(fname) - len(ext), 0):
        fname += ext
    return fname


def eval_from(fpath, err_onread=True):
    """Read a Python literal from a text file without executing code."""
    import ast

    logger.debug("Evaluating Python literal from fpath=%r", fpath)
    text = read_from(fpath)
    if text is None:
        if err_onread:
            raise Exception('Error reading: fpath=%r' % fpath)
        logger.debug("Could not evaluate missing file %r", fpath)
        return None
    try:
        return ast.literal_eval(text)
    except (SyntaxError, ValueError) as ex:
        raise ValueError(
            'File %r does not contain a valid Python literal' % fpath
        ) from ex


def read_from(fpath):
    if not os.path.exists(fpath):
        logger.debug("File does not exist: %r", fpath)
        return None
    logger.debug("Reading text file: %r", os.path.basename(fpath))
    try:
        text = read_text(fpath)
    except Exception:
        logger.exception("Error reading fpath=%r", fpath)
        raise
    if VERY_VERBOSE:
        logger.debug("Read %d characters", len(text))
    return text


def read_text(fpath, encodings=('utf-8-sig', 'mbcs', 'cp950')):
    """Read text using BOM-aware UTF-8 and available legacy encodings."""
    encoding_order = ['utf-8-sig']
    encoding_order.extend(
        encoding for encoding in encodings
        if encoding.lower() != 'utf-8-sig'
    )
    attempted = []
    last_ex = None
    for encoding in encoding_order:
        try:
            codecs.lookup(encoding)
        except LookupError as ex:
            attempted.append('%s (unavailable)' % encoding)
            last_ex = ex
            continue
        attempted.append(encoding)
        try:
            with open(fpath, 'r', encoding=encoding, errors='strict') as file:
                return file.read()
        except (LookupError, UnicodeDecodeError) as ex:
            last_ex = ex
    message = 'Could not decode %r using encodings: %s' % (
        fpath,
        ', '.join(attempted),
    )
    raise UnicodeError(message) from last_ex


def write_to(fpath, to_write):
    if PRINT_WRITES:
        logger.debug("Writing to text file: %r", fpath)
    with open(fpath, 'w', encoding='utf-8') as file:
        file.write(to_write)


def save_pkl(fpath, data):
    """Write an application-generated pickle using an explicit protocol."""
    with open(fpath, 'wb') as file:
        pickle.dump(data, file, pickle.HIGHEST_PROTOCOL)


def load_pkl(fpath):
    """Load a trusted application pickle; never use on untrusted data."""
    with open(fpath, 'rb') as file:
        return pickle.load(file)


def save_npz(fpath, *args, **kwargs):
    logger.debug("Saving NPZ: %r", fpath)
    np.savez(fpath, *args, **kwargs)
    logger.debug("Saved NPZ successfully: %r", fpath)


def load_npz_archive(fpath, expected_keys=None):
    """Safely load an NPZ archive in stored order without pickle."""
    with np.load(fpath, allow_pickle=False) as archive:
        keys = tuple(archive.files)
        if expected_keys is not None and keys != tuple(expected_keys):
            raise ValueError(
                'NPZ keys for %r were %r, expected %r' % (
                    fpath,
                    keys,
                    tuple(expected_keys),
                )
            )
        return OrderedDict((key, archive[key]) for key in keys)


def load_trusted_legacy_npz(fpath, required_keys):
    """Load a trusted HotSpotter NPZ that may contain pickled object arrays."""
    required_keys = tuple(required_keys)
    if not required_keys:
        raise ValueError('Trusted legacy NPZ loading requires expected keys')
    with np.load(fpath, allow_pickle=True, encoding='latin1') as archive:
        keys = tuple(archive.files)
        missing = tuple(key for key in required_keys if key not in keys)
        if missing:
            raise ValueError(
                'Trusted legacy NPZ %r is missing required keys %r' % (
                    fpath,
                    missing,
                )
            )
        return OrderedDict((key, archive[key]) for key in keys)


def load_npz(fpath):
    """Safely load NPZ arrays in their stored order as a tuple."""
    logger.debug("Loading NPZ: %r", os.path.basename(fpath))
    logger.debug("NPZ filesize is %s", file_megabytes_str(fpath))
    archive = load_npz_archive(fpath)
    return tuple(archive.values())


def hashstr_arr(arr, lbl='arr', **kwargs):
    if isinstance(arr, list):
        arr = tuple(arr)
    if isinstance(arr, tuple):
        arr_shape = '(' + str(len(arr)) + ')'
    else:
        arr_shape = str(arr.shape).replace(' ', '')
    arr_hash = hashstr(arr, **kwargs)
    return ''.join((lbl, '(', arr_shape, arr_hash, ')'))


def hashstr(data, trunc_pos=8):
    import ubelt as ub
    return ub.hash_data(data, base='abc')[:trunc_pos]


ALPHABET = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c',
            'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p',
            'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', ';', '=', '@',
            '[', ']', '^', '_', '`', '{', '}', '~', '!', '#', '$', '%', '&',
            '+', ',']
BIGBASE = len(ALPHABET)


def hex2_base57(hexstr):
    value = int(hexstr, 16)
    if value == 0:
        return '0'
    sign = 1 if value > 0 else -1
    value *= sign
    digits = []
    while value:
        digits.append(ALPHABET[value % BIGBASE])
        value //= BIGBASE
    if sign < 0:
        digits.append('-')
        digits.reverse()
    return ''.join(digits)


def hashstr_md5(data):
    """Return the MD5 digest of bytes or a UTF-8 encoded string."""
    if isinstance(data, str):
        data = data.encode('utf-8')
    elif isinstance(data, (bytearray, memoryview)):
        data = bytes(data)
    elif not isinstance(data, bytes):
        raise TypeError('hashstr_md5 data must be bytes-like or str')
    return hashlib.md5(data).hexdigest()


class CacheException(Exception):
    pass


def _legacy_cache_data_fpath(input_data, uid, cache_dir):
    """Return the historical unversioned cache filename unchanged."""
    hashstr_ = hashstr(input_data)
    shape_lbl = str(input_data.shape).replace(' ', '')
    data_fname = uid + '_' + shape_lbl + '_' + hashstr_ + '.npz'
    return os.path.join(cache_dir, data_fname)


def cache_hash(data):
    """Return the deterministic version-2 hash used by new cache entries."""
    array = np.asarray(data)
    if array.dtype.hasobject:
        raise TypeError('Versioned cache hashes do not support object arrays')
    canonical_dtype = array.dtype.newbyteorder('<')
    canonical = np.ascontiguousarray(array.astype(canonical_dtype, copy=False))
    descriptor = {
        'algorithm': HASH_ALGORITHM,
        'dtype': _dtype_metadata(canonical.dtype),
        'shape': [int(size) for size in canonical.shape],
    }
    hasher = hashlib.sha256()
    hasher.update(b'hotspotter-cache-hash-v2\0')
    hasher.update(
        json.dumps(descriptor, sort_keys=True, separators=(',', ':')).encode(
            'ascii'
        )
    )
    hasher.update(b'\0')
    hasher.update(canonical.tobytes(order='C'))
    return hasher.hexdigest()


def get_cache_paths(input_data, uid='', cache_dir='.'):
    """Return legacy and current cache locations for an input key."""
    input_array = np.asarray(input_data)
    shape_lbl = str(input_array.shape).replace(' ', '')
    input_hash = cache_hash(input_array)
    entry_name = uid + '_' + shape_lbl + '_' + input_hash[:16]
    current_dir = os.path.join(cache_dir, CACHE_NAMESPACE, entry_name)
    return {
        'legacy': _legacy_cache_data_fpath(input_data, uid, cache_dir),
        'current_dir': current_dir,
        'metadata': os.path.join(current_dir, 'metadata.json'),
        'data': os.path.join(current_dir, 'data.npz'),
    }


def _dtype_metadata(dtype):
    dtype = np.dtype(dtype)
    if dtype.fields is None:
        return dtype.str
    return json.loads(json.dumps(dtype.descr))


def _shape_list(shape):
    return [int(size) for size in shape]


def _validate_expected_data(data, expected_shape=None, expected_dtype=None):
    if expected_shape is not None and tuple(data.shape) != tuple(expected_shape):
        raise ValueError(
            'Cache data shape %r does not match expected shape %r' % (
                data.shape,
                tuple(expected_shape),
            )
        )
    if expected_dtype is not None and data.dtype != np.dtype(expected_dtype):
        raise ValueError(
            'Cache data dtype %r does not match expected dtype %r' % (
                data.dtype,
                np.dtype(expected_dtype),
            )
        )


def _cache_metadata(input_data, data, uid, kind):
    input_array = np.asarray(input_data)
    return {
        'cache_format_version': CACHE_FORMAT_VERSION,
        'hash_format_version': HASH_FORMAT_VERSION,
        'hash_algorithm': HASH_ALGORITHM,
        'input_hash': cache_hash(input_array),
        'input_shape': _shape_list(input_array.shape),
        'input_dtype': _dtype_metadata(input_array.dtype),
        'data_kind': kind,
        'data_shape': _shape_list(data.shape),
        'data_dtype': _dtype_metadata(data.dtype),
        'uid': uid,
    }


def _validate_metadata(metadata, input_data, uid, is_sparse):
    required_keys = {
        'cache_format_version',
        'hash_format_version',
        'hash_algorithm',
        'input_hash',
        'input_shape',
        'input_dtype',
        'data_kind',
        'data_shape',
        'data_dtype',
        'uid',
    }
    missing = required_keys.difference(metadata)
    if missing:
        raise ValueError('Cache metadata is missing keys %r' % sorted(missing))
    if metadata['cache_format_version'] != CACHE_FORMAT_VERSION:
        raise ValueError(
            'Cache format version %r does not match supported version %r' % (
                metadata['cache_format_version'],
                CACHE_FORMAT_VERSION,
            )
        )
    if metadata['hash_format_version'] != HASH_FORMAT_VERSION:
        raise ValueError(
            'Cache hash version %r does not match supported version %r' % (
                metadata['hash_format_version'],
                HASH_FORMAT_VERSION,
            )
        )
    if metadata['hash_algorithm'] != HASH_ALGORITHM:
        raise ValueError('Cache hash algorithm does not match')
    input_array = np.asarray(input_data)
    expected_values = {
        'input_hash': cache_hash(input_array),
        'input_shape': _shape_list(input_array.shape),
        'input_dtype': _dtype_metadata(input_array.dtype),
        'data_kind': 'sparse' if is_sparse else 'dense',
        'uid': uid,
    }
    for key, expected in expected_values.items():
        if metadata[key] != expected:
            raise ValueError(
                'Cache metadata %s=%r does not match expected %r' % (
                    key,
                    metadata[key],
                    expected,
                )
            )


def _atomic_json_dump(fpath, data):
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    fd, temp_path = tempfile.mkstemp(
        prefix='.metadata-',
        suffix='.tmp',
        dir=os.path.dirname(fpath),
        text=True,
    )
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as file_:
            json.dump(data, file_, sort_keys=True, separators=(',', ':'))
        os.replace(temp_path, fpath)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def _atomic_dense_save(fpath, data):
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    fd, temp_path = tempfile.mkstemp(
        prefix='.data-', suffix='.npz', dir=os.path.dirname(fpath)
    )
    os.close(fd)
    try:
        with open(temp_path, 'wb') as file_:
            np.savez(file_, data=data)
        os.replace(temp_path, fpath)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def _atomic_sparse_save(fpath, data):
    from scipy import sparse

    if not sparse.issparse(data):
        raise TypeError('Sparse cache data must be a SciPy sparse matrix')
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    fd, temp_path = tempfile.mkstemp(
        prefix='.data-', suffix='.npz', dir=os.path.dirname(fpath)
    )
    os.close(fd)
    try:
        sparse.save_npz(temp_path, data)
        os.replace(temp_path, fpath)
    except Exception:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def _save_current_cache(input_data, data, uid, cache_dir, is_sparse):
    paths = get_cache_paths(input_data, uid=uid, cache_dir=cache_dir)
    if is_sparse:
        from scipy import sparse
        if not sparse.issparse(data):
            raise TypeError('Sparse cache data must be a SciPy sparse matrix')
        cache_data = data
        kind = 'sparse'
        _atomic_sparse_save(paths['data'], cache_data)
    else:
        cache_data = np.asarray(data)
        if cache_data.dtype.hasobject:
            raise TypeError('Safe dense caches do not support object arrays')
        kind = 'dense'
        _atomic_dense_save(paths['data'], cache_data)
    metadata = _cache_metadata(input_data, cache_data, uid, kind)
    _atomic_json_dump(paths['metadata'], metadata)
    return paths


def _load_current_cache(input_data, uid, cache_dir, is_sparse,
                        expected_shape, expected_dtype):
    paths = get_cache_paths(input_data, uid=uid, cache_dir=cache_dir)
    with open(paths['metadata'], 'r', encoding='utf-8') as file_:
        metadata = json.load(file_)
    _validate_metadata(metadata, input_data, uid, is_sparse)
    if is_sparse:
        from scipy import sparse
        data = sparse.load_npz(paths['data'])
    else:
        archive = load_npz_archive(paths['data'], expected_keys=('data',))
        data = archive['data']
    if _shape_list(data.shape) != metadata['data_shape']:
        raise ValueError('Cache data shape does not match its metadata')
    if _dtype_metadata(data.dtype) != metadata['data_dtype']:
        raise ValueError('Cache data dtype does not match its metadata')
    _validate_expected_data(data, expected_shape, expected_dtype)
    return data


def _load_legacy_cache(fpath, is_sparse, expected_shape, expected_dtype):
    if is_sparse:
        from scipy import sparse
        with open(fpath, 'rb') as file_:
            data = pickle.load(file_)
        if not sparse.issparse(data):
            raise ValueError('Legacy sparse cache did not contain a sparse matrix')
    else:
        archive = load_npz_archive(fpath, expected_keys=('arr_0',))
        data = archive['arr_0']
        if data.dtype.hasobject:
            raise ValueError('Legacy dense cache contains an object array')
    _validate_expected_data(data, expected_shape, expected_dtype)
    return data


def load_cache_npz(input_data, uid='', cache_dir='.', is_sparse=False,
                   allow_legacy=True, expected_shape=None,
                   expected_dtype=None):
    """Load a validated version-2 cache, optionally migrating trusted legacy.

    Legacy sparse caches use pickle and must only be loaded from a trusted
    HotSpotter cache directory. A valid current entry always takes precedence;
    current-format validation failures never fall back to legacy data.
    """
    paths = get_cache_paths(input_data, uid=uid, cache_dir=cache_dir)
    current_exists = os.path.exists(paths['current_dir'])
    if current_exists:
        try:
            data = _load_current_cache(
                input_data,
                uid,
                cache_dir,
                is_sparse,
                expected_shape,
                expected_dtype,
            )
        except Exception as ex:
            raise CacheException(
                'Current cache validation failed for %r: %s' % (
                    paths['current_dir'],
                    ex,
                )
            ) from ex
        logger.debug("Loaded versioned cache: %r", paths['current_dir'])
        return data

    if not allow_legacy:
        raise CacheException(
            'Versioned cache does not exist: %r' % paths['current_dir']
        )
    if not os.path.exists(paths['legacy']):
        raise CacheException(
            'No current or legacy cache exists for %r' % paths['current_dir']
        )
    try:
        data = _load_legacy_cache(
            paths['legacy'],
            is_sparse,
            expected_shape,
            expected_dtype,
        )
    except Exception as ex:
        raise CacheException(
            'Legacy cache validation failed for %r: %s' % (
                paths['legacy'],
                ex,
            )
        ) from ex
    _save_current_cache(input_data, data, uid, cache_dir, is_sparse)
    logger.info(
        "Migrated legacy cache %r to version %d at %r",
        paths['legacy'],
        CACHE_FORMAT_VERSION,
        paths['current_dir'],
    )
    return data


def save_cache_npz(input_data, data, uid='', cache_dir='.', is_sparse=False):
    """Save data in the validated version-2 cache namespace."""
    paths = _save_current_cache(input_data, data, uid, cache_dir, is_sparse)
    logger.debug("Saved versioned cache: %r", paths['current_dir'])


def file_bytes(fpath):
    return os.stat(fpath).st_size


def byte_str2(nBytes):
    if nBytes < 2.0 ** 10:
        return byte_str(nBytes, 'KB')
    if nBytes < 2.0 ** 20:
        return byte_str(nBytes, 'KB')
    if nBytes < 2.0 ** 30:
        return byte_str(nBytes, 'MB')
    return byte_str(nBytes, 'GB')


def byte_str(nBytes, unit='bytes'):
    if unit.lower().startswith('b'):
        nUnit = nBytes
    elif unit.lower().startswith('k'):
        nUnit = nBytes / (2.0 ** 10)
    elif unit.lower().startswith('m'):
        nUnit = nBytes / (2.0 ** 20)
    elif unit.lower().startswith('g'):
        nUnit = nBytes / (2.0 ** 30)
    else:
        raise NotImplementedError(
            'unknown nBytes=%r unit=%r' % (nBytes, unit)
        )
    return '%.2f %s' % (nUnit, unit)


def file_megabytes(fpath):
    return os.stat(fpath).st_size / (2.0 ** 20)


def file_megabytes_str(fpath):
    return '%.2f MB' % file_megabytes(fpath)
