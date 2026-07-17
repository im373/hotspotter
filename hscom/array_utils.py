"""List and NumPy helpers with no dependency on the compatibility façade."""

from collections import OrderedDict
from itertools import product as iprod
import math

import numpy as np

from .logging_utils import DEPRECATED


def intersect_ordered(list1, list2):
    """Return elements shared with list2 while preserving list1 order."""
    set2 = set(list2)
    return [item for item in list1 if item in set2]


@DEPRECATED
def array_index(array, item):
    return np.where(array == item)[0][0]


@DEPRECATED
def index_of(item, array):
    """Return the first index of item in array."""
    return np.where(array == item)[0][0]


def list_index(search_list, to_find_list):
    """Return the first index of each requested item in search_list."""
    search_array = np.asarray(search_list)
    indexes = []
    for item in to_find_list:
        matches = np.where(search_array == item)[0]
        if len(matches) == 0:
            raise ValueError('Item %r was not found in the search list' % item)
        indexes.append(int(matches[0]))
    return indexes


def list_eq(list_):
    if len(list_) == 0:
        return True
    item0 = list_[0]
    return all(item == item0 for item in list_)


def intersect2d_numpy(A, B):
    nrows, ncols = A.shape
    assert A.dtype == B.dtype, 'A and B must have the same dtypes'
    dtype = np.dtype([('f%d' % index, A.dtype) for index in range(ncols)])
    try:
        common = np.intersect1d(A.view(dtype), B.view(dtype))
    except ValueError:
        common = np.intersect1d(A.copy().view(dtype), B.copy().view(dtype))
    return common.view(A.dtype).reshape(-1, ncols)


def intersect2d(A, B):
    A = np.asarray(A)
    B = np.asarray(B)
    if A.ndim != 2 or B.ndim != 2 or A.shape[1] != B.shape[1]:
        raise ValueError('A and B must be 2D arrays with equal column counts')
    common_rows = set(map(tuple, A)).intersection(map(tuple, B))
    Ax = np.array(
        [index for index, row in enumerate(A) if tuple(row) in common_rows],
        dtype=int,
    )
    Bx = np.array(
        [index for index, row in enumerate(B) if tuple(row) in common_rows],
        dtype=int,
    )
    seen = set()
    ordered_rows = []
    for row in A:
        row_tuple = tuple(row)
        if row_tuple in common_rows and row_tuple not in seen:
            seen.add(row_tuple)
            ordered_rows.append(row)
    common = np.asarray(ordered_rows, dtype=A.dtype).reshape(-1, A.shape[1])
    return common, Ax, Bx


def unique_keep_order(arr):
    import pandas as pd
    return pd.unique(arr)


def mystats(_list):
    if len(_list) == 0:
        return {'empty_list': True}
    nparr = np.array(_list)
    min_val = nparr.min()
    max_val = nparr.max()
    nMin = np.sum(nparr == min_val)
    nMax = np.sum(nparr == max_val)
    # Preserve the historical float32 values while returning Python scalars.
    return OrderedDict([('max', float(np.float32(max_val))),
                        ('min', float(np.float32(min_val))),
                        ('mean', float(np.float32(nparr.mean()))),
                        ('std', float(np.float32(nparr.std()))),
                        ('nMin', int(nMin)),
                        ('nMax', int(nMax)),
                        ('shape', repr(nparr.shape))])


def printable_mystats(_list, newlines=False):
    stat_dict = mystats(_list)
    # NumPy float32 had a shorter string representation than Python float.
    # Format these fields through float32 to keep existing diagnostics stable.
    float_keys = {'max', 'min', 'mean', 'std'}
    stat_strs = [
        '%r: %s' % (
            key,
            np.float32(val) if key in float_keys else val,
        )
        for key, val in stat_dict.items()
    ]
    if newlines:
        indent = '    '
        head = '{\n' + indent
        sep = ',\n' + indent
        tail = '\n}'
    else:
        head = '{'
        sep = ', '
        tail = '}'
    return head + sep.join(stat_strs) + tail


def pstats(*args, **kwargs):
    return printable_mystats(*args, **kwargs)


def numpy_list_num_bits(nparr_list, expected_type, expected_dims):
    num_bits = 0
    num_items = 0
    num_elemt = 0
    expected_dtype = np.dtype(expected_type)
    bit_per_item = expected_dtype.itemsize * 8
    for nparr in nparr_list:
        arr_len, arr_dims = nparr.shape
        if nparr.dtype != expected_dtype:
            msg = 'Expected Type: ' + repr(expected_type)
            msg += 'Got Type: ' + repr(nparr.dtype)
            raise Exception(msg)
        if arr_dims != expected_dims:
            msg = 'Expected Dims: ' + repr(expected_dims)
            msg += 'Got Dims: ' + repr(arr_dims)
            raise Exception(msg)
        num_bits += len(nparr) * expected_dims * bit_per_item
        num_elemt += len(nparr) * expected_dims
        num_items += len(nparr)
    return num_bits, num_items, num_elemt


def alloc_lists(num_alloc):
    return [[] for _ in range(num_alloc)]


def ensure_list_size(list_, size_):
    lendiff = size_ - len(list_)
    if lendiff > 0:
        list_.extend([None for _ in range(lendiff)])


def tiled_range(range, cols):
    return np.tile(np.arange(range), (cols, 1)).T


def random_indexes(max_index, subset_size):
    subst_ = np.arange(0, max_index)
    np.random.shuffle(subst_)
    return subst_[0:min(subset_size, max_index)]


def correct_zeros(M):
    index_gen = iprod(*[range(_) for _ in M.shape])
    for index in index_gen:
        if M[index] < 1E-18:
            M[index] = 0
    return M


def normalize(array, dim=0):
    return norm_zero_one(array, dim)


def norm_zero_one(array, dim=0):
    """Normalize an array to [0, 1], mapping constant ranges to zero."""
    array = np.asarray(array)
    array_max = array.max(axis=dim, keepdims=True)
    array_min = array.min(axis=dim, keepdims=True)
    array_exnt = np.subtract(array_max, array_min)
    numerator = np.subtract(array, array_min)
    return np.divide(
        numerator,
        array_exnt,
        out=np.zeros_like(numerator, dtype=float),
        where=array_exnt != 0,
    )


def find_std_inliers(data, m=2):
    return abs(data - np.mean(data)) < m * np.std(data)


def choose(n, k):
    """Return the exact binomial coefficient for scalar integers."""
    return math.comb(n, k)


def cartesian(arrays, out=None):
    arrays = [np.asarray(x) for x in arrays]
    if not arrays:
        raise ValueError('cartesian requires at least one input array')
    if any(array.ndim != 1 for array in arrays):
        raise ValueError('cartesian inputs must be one-dimensional')
    dtype = arrays[0].dtype
    n = math.prod(int(x.size) for x in arrays)
    if out is None:
        out = np.zeros([n, len(arrays)], dtype=dtype)
    if n == 0:
        return out
    m = n // int(arrays[0].size)
    out[:, 0] = np.repeat(arrays[0], m)
    if arrays[1:]:
        cartesian(arrays[1:], out=out[0:m, 1:])
        for index in range(1, arrays[0].size):
            out[index * m:(index + 1) * m, 1:] = out[0:m, 1:]
    return out


def ensure_iterable(obj):
    if np.iterable(obj):
        return obj
    return [obj]


def npfind(arr):
    found = np.where(arr)[0]
    return -1 if len(found) == 0 else found[0]


def all_dict_combinations(varied_dict):
    varied_items = iter(varied_dict.items())
    tup_lists = [
        [(key, val) for val in val_list]
        for key, val_list in varied_items
    ]
    return [
        {key: val for key, val in tups}
        for tups in iprod(*tup_lists)
    ]
