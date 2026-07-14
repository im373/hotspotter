# HotSpotter port notes:
# Updated shared compatibility helpers for Python 3, NumPy 2, and Windows paths.
# Kept logging, preferences, file I/O, and argument handling aligned with modern runtimes.


# Python
import logging
import os
import fnmatch
import pickle
from os.path import normpath, exists, realpath, join, expanduser, dirname
import datetime
import time
import sys
# Science
import numpy as np
import cv2
from PIL import Image
from PIL.ExifTags import TAGS
# Hotspotter
from .dev_utils import make_reloader
from . import helpers
from .profiling import profile

logger = logging.getLogger(__name__)
rrr = make_reloader(__name__, '[io]')

VERBOSE_IO = 0  # 2

ENABLE_SMART_FNAME_HASHING = False

if sys.platform.startswith('win32'):
    ENABLE_SMART_FNAME_HASHING = True


# --- Saving ---
def save_npy(fpath, data):
    with open(fpath, 'wb') as file:
        np.save(file, data)


def save_npz(fpath, data):
    with open(fpath, 'wb') as file:
        np.savez(file, data)


def save_cPkl(fpath, data):
    with open(fpath, 'wb') as file:
        pickle.dump(data, file, pickle.HIGHEST_PROTOCOL)


def save_pkl(fpath, data):
    with open(fpath, 'wb') as file:
        pickle.dump(data, file, pickle.HIGHEST_PROTOCOL)


# --- Loading ---
def _pickle_load_py2_compatible(file):
    """Load pickle data, falling back to Python 2 byte-string encoding."""
    try:
        return pickle.load(file)
    except UnicodeDecodeError:
        file.seek(0)
        return pickle.load(file, encoding='latin1')


def _np_load_py2_compatible(file, **kwargs):
    """Load NumPy data that may contain pickled Python 2 object arrays."""
    kwargs.setdefault('allow_pickle', True)
    kwargs.setdefault('encoding', 'latin1')
    return np.load(file, **kwargs)


def load_npz_memmap(fpath):
    with open(fpath, 'rb') as file:
        npz = _np_load_py2_compatible(file, mmap_mode='r')
        data = npz['arr_0']
        npz.close()
    return data


def load_npz(fpath):
    with open(fpath, 'rb') as file:
        npz = _np_load_py2_compatible(file, mmap_mode=None)
        data = npz['arr_0']
        npz.close()
    return data


def load_npy(fpath):
    with open(fpath, 'rb') as file:
        data = _np_load_py2_compatible(file)
    return data


def load_cPkl(fpath):
    with open(fpath, 'rb') as file:
        data = _pickle_load_py2_compatible(file)
    return data


def load_pkl(fpath):
    with open(fpath, 'rb') as file:
        data = _pickle_load_py2_compatible(file)
    return data


ext2_load_func = {
    '.npy': load_npy,
    '.npz': load_npz,
    '.cPkl': load_cPkl,
    '.pkl': load_pkl}


ext2_save_func = {
    '.npy': save_npy,
    '.npz': save_npz,
    '.cPkl': save_cPkl,
    '.pkl': save_pkl}


def debug_smart_load(dpath='', fname='*', uid='*', ext='*'):
    pattern = fname + uid + ext
    logger.debug(f"debug_smart_load(): dpath={dpath!r}")
    for fname_ in os.listdir(dpath):
        if fnmatch.fnmatch(fname_, pattern):
            #fpath = join(dpath, fname_)
            logger.debug(f"{fname_}")


# --- Smart Load/Save ---
@profile
def __args2_fpath(dpath, fname, uid, ext):
    if len(ext) > 0 and ext[0] != '.':
        raise Exception('Fatal Error: Please be explicit and use a dot in ext')
    fname_uid = fname + uid
    if len(fname_uid) > 128:
        fname_uid = fname + '_' + helpers.hashstr(fname_uid, 8)
    fpath = join(dpath, fname_uid + ext)
    fpath = normpath(fpath)
    return fpath


@profile
def smart_fname_info(func_name, dpath, fname, uid, ext):
    info_list = [
        'dpath=%r' % dpath,
        'uid=%r' % (uid),
        'fname=%r, ext=%r' % (fname, ext),
    ]
    indent = '\n' + (' ' * 11)
    return ('[io] ' + func_name + '(' + indent + indent.join(info_list) + ')')


@profile
def smart_save(data, dpath='', fname='', uid='', ext='', verbose=VERBOSE_IO):
    ''' Saves data to the direcotry speficied '''
    helpers.ensuredir(dpath)
    fpath = __args2_fpath(dpath, fname, uid, ext)
    if verbose:
        if verbose > 1:
            logger.info("")
        logger.info(f"{smart_fname_info('smart_save', dpath, fname, uid, ext)}")
    ret = __smart_save(data, fpath, verbose)
    if verbose > 1:
        logger.info("")
    return ret


@profile
def smart_load(dpath='', fname='', uid='', ext='', verbose=VERBOSE_IO, **kwargs):
    ''' Loads data to the direcotry speficied '''
    fpath = __args2_fpath(dpath, fname, uid, ext)
    if verbose:
        if verbose > 1:
            logger.info("")
        logger.info(f"{smart_fname_info('smart_load', dpath, fname, uid, ext)}")
    data = __smart_load(fpath, verbose, **kwargs)
    if verbose > 1:
        logger.info("")
    return data


@profile
def __smart_save(data, fpath, verbose):
    ' helper '
    dpath, fname = os.path.split(fpath)
    fname_noext, ext_ = os.path.splitext(fname)
    save_func = ext2_save_func[ext_]
    if verbose > 1:
        logger.info(f"saving: {type(data)!r}")
    try:
        save_func(fpath, data)
        if verbose > 1:
            logger.info(f"saved {filesize_str(fpath)}")
    except Exception as ex:
        logger.exception(f"Exception while saving {fpath!r}")
        raise


@profile
def __smart_load(fpath, verbose, allow_alternative=False, can_fail=True, **kwargs):
    ' helper '
    # Get components of the filesname
    dpath, fname = os.path.split(fpath)
    fname_noext, ext_ = os.path.splitext(fname)
    # If exact path doesnt exist
    if not exists(fpath):
        logger.warning(f"fname={fname!r} does not exist")
        if allow_alternative:
            # allows alternative extension
            convert_alternative(fpath, verbose, can_fail=can_fail, **kwargs)
    # Ensure a valid extension
    if ext_ == '':
        raise NotImplementedError('')
    else:
        load_func = ext2_load_func[ext_]
        # Do actual data loading
        try:
            if verbose > 1:
                logger.info(f"loading {filesize_str(fpath)}")
            data = load_func(fpath)
            if verbose:
                logger.info("loaded data")
        except Exception as ex:
            if verbose:
                logger.exception(f"Exception while loading {fpath!r}")
            data = None
            if not can_fail:
                raise
    if data is None:
        if verbose:
            logger.warning(f"did not load {fpath!r}")
    return data
#----


# --- Util ---
@profile
def convert_alternative(fpath, verbose, can_fail):
    # check for an alternative (maybe old style or ext) file
    alternatives = find_alternatives(fpath, verbose)
    dpath, fname = os.path.split(fpath)
    if len(alternatives) == 0:
        fail_msg = '[io] ...no alternatives to %r' % fname
        if verbose:
            logger.warning(f"{fail_msg}")
        if can_fail:
            return None
        else:
            raise IOError(fail_msg)
    else:
        #load and convert alternative
        alt_fpath = alternatives[0]
        if verbose > 1:
            logger.info(f"converting {alt_fpath!r}")
        data = __smart_load(alt_fpath, verbose, allow_alternative=False)
        __smart_save(data, fpath, verbose)
        return data


@profile
def find_alternatives(fpath, verbose):
    # Check if file is in another format
    dpath, fname = os.path.split(fpath)
    fname_noext, ext_ = os.path.splitext(fname)
    fpath_noext = join(dpath, fname_noext)
    alternatives = []
    # Find files with a different
    for alt_ext in list(['.npy', '.npz', '.cPkl', '.pkl']):
        alt_fpath = fpath_noext + alt_ext
        if exists(alt_fpath):
            alternatives.append(alt_fpath)
    if verbose > 1:
        # Print num alternatives / filesizes
        logger.info(f"Found {len(alternatives)} alternate(s)")
        for alt_fpath in iter(alternatives):
            logger.info(f"{filesize_str(alt_fpath)}")
    return alternatives


def sanatize_fpath(fpath, ext=None):  # UNUSED!
    'Ensures a filepath has correct the extension'
    dpath, fname = os.path.split(fpath)
    fname_noext, ext_ = os.path.splitext(fname)
    if not ext is None and ext_ != ext:
        fname = fname_noext + ext
    fpath = normpath(join(dpath, fname))
    return fpath


@profile
def filesize_str(fpath):
    _, fname = os.path.split(fpath)
    mb_str = helpers.file_megabytes_str(fpath)
    return 'filesize(%r)=%s' % (fname, mb_str)


@profile
def exiftime_to_unixtime(datetime_str):
    try:
        dt = datetime.datetime.strptime(datetime_str, '%Y:%m:%d %H:%M:%S')
        return time.mktime(dt.timetuple())
    except TypeError:
        #if datetime_str is None:
            #return -1
        return -1
    except ValueError as ex:
        if isinstance(datetime_str, str) or isinstance(datetime_str, str):
            if datetime_str.find('No EXIF Data') == 0:
                return -1
            if datetime_str.find('Invalid') == 0:
                return -1
            if datetime_str == '0000:00:00 00:00:00':
                return -1
        logger.exception(f"Could not parse EXIF datetime {datetime_str!r} of type {type(datetime_str)!r}")
        raise


@profile
def check_exif_keys(pil_image):
    info_ = pil_image._getexif()
    valid_keys = []
    invalid_keys = []
    for key, val in info_.items():
        try:
            exif_keyval = TAGS[key]
            valid_keys.append((key, exif_keyval))
        except KeyError:
            invalid_keys.append(key)
    logger.info(f"valid_keys = {valid_keys!r}")
    #import draw_func2 as df2
    #exec(df2.present())


@profile
def read_all_exif_tags(pil_image):
    info_ = pil_image._getexif()
    info_iter = iter(info_.items())
    tag_ = lambda key: TAGS.get(key, key)
    exif = {} if info_ is None else {tag_(k): v for k, v in info_iter}
    return exif


@profile
def read_one_exif_tag(pil_image, tag):
    try:
        exif_key = list(TAGS.keys())[list(TAGS.values()).index(tag)]
    except ValueError:
        return 'Invalid EXIF Tag'
    info_ = pil_image._getexif()
    if info_ is None:
        return None
    else:
        invalid_str = 'Invalid EXIF Key: exif_key=%r, tag=%r' % (exif_key, tag)
        exif_val = info_.get(exif_key, invalid_str)
    return exif_val
    #try:
        #exif_val = info_[exif_key]
    #except KeyError:
        #exif_val = 'Invalid EXIF Key: exif_key=%r, tag=%r' % (exif_key, tag)
        #print('')
        #print(exif_val)
        #check_exif_keys(pil_image)


@profile
def read_exif(fpath, tag=None):
    try:
        pil_image = Image.open(fpath)
        if not hasattr(pil_image, '_getexif'):
            return 'No EXIF Data'
    except IOError as ex:
        from . import argparse2
        logger.exception(f"Caught IOError reading EXIF from {fpath!r}")
        print_image_checks(fpath)
        if argparse2.ARGS_.strict:
            raise
        return {} if tag is None else None
    if tag is None:
        exif = read_all_exif_tags(pil_image)
    else:
        exif = read_one_exif_tag(pil_image, tag)
    del pil_image
    return exif


@profile
def print_image_checks(img_fpath):
    hasimg = helpers.checkpath(img_fpath, verbose=True)
    if hasimg:
        _tup = (img_fpath, filesize_str(img_fpath))
        logger.warning(f"Image {_tup[0]!r} ({_tup[1]}) exists. Is it corrupted?")
    else:
        logger.warning(f"Image {img_fpath!r} does not exist")
    return hasimg


@profile
def read_exif_list(fpath_list, **kwargs):
    def _gen(fpath_list):
        # Exif generator
        nGname = len(fpath_list)
        lbl = '[io] Load Image EXIF'
        mark_progress, end_progress = helpers.progress_func(nGname, lbl, 16)
        for count, fpath in enumerate(fpath_list):
            mark_progress(count)
            yield read_exif(fpath, **kwargs)
        end_progress()
    exif_list = [exif for exif in _gen(fpath_list)]
    return exif_list


@profile
def imread(img_fpath, mode=None):
    try:
        img_fpath = os.fspath(img_fpath)
        # opencv always reads in BGR mode (fastest load time)
        load_color = getattr(cv2, 'IMREAD_COLOR', None)
        if load_color is None:
            load_color = cv2.IMREAD_COLOR if hasattr(cv2, 'IMREAD_COLOR') else cv2.CV_LOAD_IMAGE_COLOR
        imgBGR = cv2.imread(img_fpath, flags=load_color)
        if imgBGR is None:
            # OpenCV can fail on Windows Unicode paths; retry through imdecode.
            try:
                imgBGR = cv2.imdecode(np.fromfile(img_fpath, dtype=np.uint8),
                                      load_color)
            except Exception:
                imgBGR = None
        if imgBGR is None:
            raise IOError('cv2 failed to read image: %r' % (img_fpath,))
        if mode is not None and mode != 'BRG':
            # RGB is a good standard and makes physical sense
            if mode == 'RGB':
                return cv2.cvtColor(imgBGR, cv2.COLOR_BGR2RGB)
            # LAB simulates human perception. Great for color comparisons
            if mode == 'LAB':
                return cv2.cvtColor(imgBGR, cv2.COLOR_BGR2LAB)
            # HSV is also good for perception and more intuitive than LAB
            if mode == 'HSV':
                return cv2.cvtColor(imgBGR, cv2.COLOR_BGR2HSV)
        return imgBGR
    except Exception as ex:
        logger.exception(f"ERROR reading image {img_fpath!r}")
        raise


DUPLICATE_HASH_PRECISION = 32


def detect_duplicate_images(imgpath_list):
    import sys
    global DUPLICATE_HASH_PRECISION
    nImg = len(imgpath_list)
    lbl = 'checking duplicate'
    duplicates = {}
    mark_progress, end_progress = helpers.progress_func(nImg, lbl=lbl)
    for count, gpath in enumerate(imgpath_list):
        mark_progress(count)
        img = imread(gpath)
        img_hash = helpers.hashstr(img, DUPLICATE_HASH_PRECISION)
        if not img_hash in duplicates:
            duplicates[img_hash] = []
        duplicates[img_hash].append(gpath)

    if '--strict' in sys.argv:
        # Be very safe: Check for collisions
        for hashstr, gpath_list in duplicates.items():
            img1 = imread(gpath_list[0])
            for gpath in gpath_list:
                img2 = imread(gpath)
                if not np.all(img1 == img2):
                    DUPLICATE_HASH_PRECISION += 8
                    raise Exception("hash collision. try again")
    end_progress()
    return duplicates


# --- Standard Images ---


def get_hsdir():
    import sys
    if getattr(sys, 'frozen', False):
        hsdir = dirname(sys.executable)
    elif __file__:
        hsdir = dirname((dirname(__file__)))
    return hsdir


def splash_img_fpath():
    hsdir = dirname(__file__)
    splash_fpath = realpath(join(hsdir, '../hsgui/_frontend/splash.png'))
    return splash_fpath


# --- Global Cache ---
# TODO: This doesnt belong here
HOME = expanduser('~')
#GLOBAL_CACHE_DIR = realpath('.hotspotter/global_cache')
GLOBAL_CACHE_DIR = join(HOME, '.hotspotter/global_cache')
helpers.ensuredir(GLOBAL_CACHE_DIR)


def global_cache_read(cache_id, default='.'):
    cache_fname = join(GLOBAL_CACHE_DIR, 'cached_dir_%s.txt' % cache_id)
    return helpers.read_from(cache_fname) if exists(cache_fname) else default


def global_cache_write(cache_id, newdir):
    cache_fname = join(GLOBAL_CACHE_DIR, 'cached_dir_%s.txt' % cache_id)
    helpers.write_to(cache_fname, newdir)


def delete_global_cache():
    global_cache_dir = GLOBAL_CACHE_DIR
    helpers.remove_files_in_dir(global_cache_dir, recursive=True, verbose=True,
                                dryrun=False)


# --- Shelve Caching ---
#def read_cache(fpath):
    #pass
#def write_cache(fpath):
    #with open(fpath, 'wa') as file_
        #shelf = shelve.open(file_)
#def cached_keys(fpath):
    #pass
