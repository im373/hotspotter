"""Low-level path discovery and image-file helpers."""

import fnmatch
import os
from os.path import expanduser, join, relpath


_IMG_EXTS = ['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.ppm']
_LOWER_EXTS = [ext.lower() for ext in _IMG_EXTS]
_UPPER_EXTS = [ext.upper() for ext in _IMG_EXTS]
IMG_EXTENSIONS = set(_LOWER_EXTS + _UPPER_EXTS)


def try_get_path(path_list):
    tried_list = []
    for path in path_list:
        if '~' in path:
            path = expanduser(path)
        tried_list.append(path)
        if os.path.exists(path):
            return path
    return False, tried_list


def matches_image(fname):
    fname_ = fname.lower()
    img_pats = ['*' + ext for ext in IMG_EXTENSIONS]
    return any(fnmatch.fnmatch(fname_, pattern) for pattern in img_pats)


def num_images_in_dir(path):
    """Return the number of recognized image files beneath path."""
    num_imgs = 0
    for root, dirs, files in os.walk(path):
        for fname in files:
            if matches_image(fname):
                num_imgs += 1
    return num_imgs


def list_images(img_dpath, ignore_list=None, recursive=True, fullpath=False):
    if ignore_list is None:
        ignore_list = []
    if not os.path.exists(img_dpath):
        raise AssertionError('Asserted path does not exist: ' + img_dpath)
    ignore_set = set(ignore_list)
    gname_list_ = []
    for root, dlist, flist in os.walk(img_dpath):
        for fname in flist:
            gname = join(relpath(root, img_dpath), fname)
            gname = gname.replace('\\', '/').replace('./', '')
            if fullpath:
                gname_list_.append(join(root, gname))
            else:
                gname_list_.append(gname)
        if not recursive:
            break
    return [
        gname for gname in gname_list_
        if gname not in ignore_set and matches_image(gname)
    ]
