# HotSpotter port notes:
# Updated shared compatibility helpers for Python 3, NumPy 2, and Windows paths.
# Kept logging, preferences, file I/O, and argument handling aligned with modern runtimes.

"""Legacy HotSpotter utility compatibility façade.

Focused implementations are progressively extracted into lower-level modules.
Historical imports through ``hscom.helpers`` remain supported by re-exports.
"""

# Scientific
import numpy as np
# Standard
from itertools import chain
from os.path import (join, relpath, normpath, split, isdir, isfile, exists,
                     islink, ismount)
import pickle
import io
import datetime
import fnmatch
import inspect
import logging
import os
import platform
import shutil
import sys
import textwrap
import time
import types
# HotSpotter
from .dev_utils import make_reloader
from .array_utils import (
    alloc_lists,
    all_dict_combinations,
    array_index,
    cartesian,
    choose,
    correct_zeros,
    ensure_iterable,
    ensure_list_size,
    find_std_inliers,
    index_of,
    intersect2d,
    intersect2d_numpy,
    intersect_ordered,
    list_eq,
    list_index,
    mystats,
    norm_zero_one,
    normalize,
    npfind,
    numpy_list_num_bits,
    printable_mystats,
    pstats,
    random_indexes,
    tiled_range,
    unique_keep_order,
)
from .logging_utils import DEPRECATED
from .path_utils import (
    IMG_EXTENSIONS,
    list_images,
    matches_image,
    num_images_in_dir,
    try_get_path,
)
from .formatting import (
    commas,
    float_to_decimal,
    format,
    horiz_string,
    indent,
    indent_list,
    int_comma_str,
    joins,
    num_fmt,
    pack_into,
    remove_chars,
    sigfig_str,
    str2,
    truncate_str,
    fewest_digits_float_str,
)
from .progress import (
    VALID_PROGRESS_TYPES,
    progress_func,
    progress_str,
    simple_progres_func,
)
from . import serialization as _serialization
from .serialization import (
    ALPHABET,
    BIGBASE,
    CACHE_FORMAT_VERSION,
    CACHE_NAMESPACE,
    HASH_ALGORITHM,
    HASH_FORMAT_VERSION,
    LEGACY_HASH_FORMAT_VERSION,
    CacheException,
    byte_str,
    byte_str2,
    cache_hash,
    file_bytes,
    file_megabytes,
    file_megabytes_str,
    hashstr,
    hashstr_arr,
    hashstr_md5,
    hex2_base57,
    get_cache_paths,
    load_cache_npz,
    load_npz,
    load_npz_archive,
    load_pkl,
    load_trusted_legacy_npz,
    read_text,
    sanatize_fname,
    sanatize_fname2,
    save_cache_npz,
    save_npz,
    save_pkl,
)
from . import tools
from .Printable import printableVal

logger = logging.getLogger(__name__)
rrr = make_reloader(__name__, '[util]')


@DEPRECATED
def print_(msg=''):
    """Compatibility wrapper for historical debug output."""
    logger.debug("%s", str(msg).rstrip())

@DEPRECATED
def print_on():
    """Compatibility no-op for legacy modules that toggled helper printing."""

@DEPRECATED
def print_off():
    """Compatibility no-op for legacy modules that toggled helper printing."""

@DEPRECATED
def printDBG(msg):
    """Compatibility wrapper for historical debug output."""
    logger.debug("%s", msg)

# --- Globals ---

PRINT_CHECKS = False  # True
__PRINT_WRITES__ = False
__CHECKPATH_VERBOSE__ = False

VERY_VERBOSE = False


def horiz_print(*args):
    toprint = horiz_string(args)
    logger.debug("%s", toprint)


# --- Lists ---
def list_replace(instr, search_list=None, repl_list=None):
    if search_list is None:
        search_list = []
    repl_list = [''] * len(search_list) if repl_list is None else repl_list
    for ser, repl in zip(search_list, repl_list):
        instr = instr.replace(ser, repl)
    return instr


def myprint(input=None, prefix='', indent='', lbl=''):
    if len(lbl) > len(prefix):
        prefix = lbl
    if len(prefix) > 0:
        prefix += ' '
    logger.debug("%s", indent + prefix + str(type(input)) + ' ')
    if isinstance(input, list):
        logger.debug("%s", indent + '[')
        for item in iter(input):
            myprint(item, indent=indent + '  ')
        logger.debug("%s", indent + ']')
    elif isinstance(input, str):
        logger.debug("%s", input)
    elif isinstance(input, dict):
        logger.debug("%s", printableVal(input))
    else:
        logger.debug("%s", indent + '{')
        attribute_list = dir(input)
        for attr in attribute_list:
            if attr.find('__') == 0:
                continue
            val = str(input.__getattribute__(attr))
            #val = input[attr]
            # Format methods nicer
            #if val.find('built-in method'):
                #val = '<built-in method>'
            logger.debug("%s  %s : %s", indent, attr, val)
        logger.debug("%s", indent + '}')


def info(var, lbl):
    if isinstance(var, np.ndarray):
        return npinfo(var, lbl)
    if isinstance(var, list):
        return listinfo(var, lbl)


def npinfo(ndarr, lbl='ndarr'):
    info = ''
    info += (lbl + ': shape=%r ; dtype=%r' % (ndarr.shape, ndarr.dtype))
    return info


def listinfo(list_, lbl='ndarr'):
    if not isinstance(list_, list):
        raise Exception('!!')
    info = ''
    type_set = set([])
    for _ in iter(list_):
        type_set.add(str(type(_)))
    info += (lbl + ': len=%r ; types=%r' % (len(list_), type_set))
    return info


#expected_type = np.float32
#expected_dims = 5
def get_timestamp(format_='filename', use_second=False):
    now = datetime.datetime.now()
    if use_second:
        time_tup = (now.year, now.month, now.day, now.hour, now.minute, now.second)
        time_formats = {
            'filename': 'ymd_hms-%04d-%02d-%02d_%02d-%02d-%02d',
            'comment': '# (yyyy-mm-dd hh:mm:ss) %04d-%02d-%02d %02d:%02d:%02d'}
    else:
        time_tup = (now.year, now.month, now.day, now.hour, now.minute)
        time_formats = {
            'filename': 'ymd_hm-%04d-%02d-%02d_%02d-%02d',
            'comment': '# (yyyy-mm-dd hh:mm) %04d-%02d-%02d %02d:%02d'}
    stamp = time_formats[format_] % time_tup
    return stamp

def get_computer_name():
    return platform.node()


def win_shortcut(source, link_name):
    import ctypes
    csl = ctypes.windll.kernel32.CreateSymbolicLinkW
    csl.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
    csl.restype = ctypes.c_ubyte
    flags = 1 if isdir(source) else 0
    retval = csl(link_name, source, flags)
    if retval == 0:
        #warn_msg = '[helpers] Unable to create symbolic link on windows.'
        #print(warn_msg)
        #warnings.warn(warn_msg, category=UserWarning)
        if checkpath(link_name):
            return True
        raise ctypes.WinError()


def symlink(source, link_name, noraise=False):
    if os.path.islink(link_name):
        logger.debug('[helpers] symlink %r exists', link_name)
        return
    logger.debug(
        '[helpers] Creating symlink: source=%r link_name=%r',
        source,
        link_name,
    )
    try:
        os_symlink = getattr(os, "symlink", None)
        if callable(os_symlink):
            os_symlink(source, link_name)
        else:
            win_shortcut(source, link_name)
    except Exception:
        checkpath(link_name, True)
        checkpath(source, True)
        if not noraise:
            raise


# --- Convinience ----
def vd(dname=None):
    'view directory'
    from . import cross_platform
    cross_platform.view_directory(dname)


#def gvim(fname):
    #'its the only editor that matters'
    #import subprocess
    #proc = subprocess.Popen(['gvim',fname])


@DEPRECATED
def cmd(command):
    """Deprecated unsafe shell helper; use ``subprocess.run`` explicitly."""
    os.system(command)


# --- Path ---
@DEPRECATED
def filecheck(fpath):
    """Deprecated compatibility alias for ``os.path.exists``."""
    return exists(fpath)


@DEPRECATED
def dircheck(dpath, makedir=True):
    if not exists(dpath):
        if not makedir:
            #print('Nonexistant directory: %r ' % dpath)
            return False
        logger.debug('Making directory: %r', dpath)
        os.makedirs(dpath)
    return True


def remove_file(fpath, verbose=True, dryrun=False, **kwargs):
    try:
        if dryrun:
            if verbose:
                logger.debug('[helpers] Dryrem %r', fpath)
        else:
            if verbose:
                logger.debug('[helpers] Removing %r', fpath)
            os.remove(fpath)
    except OSError as e:
        logger.warning('OSError: %s; could not delete %s', e, fpath)
        return False
    return True


def remove_dirs(dpath, dryrun=False, **kwargs):
    if dryrun:
        logger.debug(
            '[helpers] Dry run: would remove directory: %r',
            dpath,
        )
        return True
    logger.debug('[helpers] Removing directory: %r', dpath)
    try:
        if islink(dpath):
            os.unlink(dpath)
        else:
            shutil.rmtree(dpath)
    except OSError as e:
        logger.warning('OSError: %s; could not delete %s', e, dpath)
        return False
    return True


def remove_files_in_dir(dpath, fname_pattern='*', recursive=False, verbose=True,
                        dryrun=False, **kwargs):
    logger.debug(
        '[helpers] Removing files in %r matching %r (recursive=%r)',
        dpath,
        fname_pattern,
        recursive,
    )
    num_removed, num_matched = (0, 0)
    if not exists(dpath):
        msg = ('!!! dir = %r does not exist!' % dpath)
        logger.warning("%s", msg)
    for root, dname_list, fname_list in os.walk(dpath):
        for fname in fnmatch.filter(fname_list, fname_pattern):
            num_matched += 1
            num_removed += remove_file(join(root, fname), verbose=verbose,
                                       dryrun=dryrun, **kwargs)
        if not recursive:
            break
    logger.debug('[helpers] Removed %d/%d files', num_removed, num_matched)
    return True


def delete(path, dryrun=False, recursive=True, verbose=True, **kwargs):
    logger.debug('[helpers] Deleting path=%r', path)
    rmargs = dict(dryrun=dryrun, recursive=recursive, verbose=verbose, **kwargs)
    if not exists(path):
        msg = ('..does not exist!')
        logger.debug("%s", msg)
        return False
    if isdir(path):
        flag = remove_files_in_dir(path, **rmargs)
        flag = flag and remove_dirs(path, **rmargs)
    elif isfile(path):
        flag = remove_file(path, **rmargs)
    return flag


def longest_existing_path(_path):
    while True:
        _path_new = os.path.dirname(_path)
        if exists(_path_new):
            _path = _path_new
            break
        if _path_new == _path:
            logger.warning('Malformed path has no existing parent: %r', _path)
            _path = ''
            break
        _path = _path_new
    return _path


def path_ndir_split(path, n):
    path, ndirs = split(path)
    for i in range(n - 1):
        path, name = split(path)
        ndirs = name + os.path.sep + ndirs
    return ndirs


def get_caller_name():
    frame = inspect.currentframe()
    frame = frame.f_back
    caller_name = None
    while caller_name in [None, 'ensurepath']:
        frame = frame.f_back
        if frame is None:
            break
        caller_name = frame.f_code.co_name
    return caller_name


def checkpath(path_, verbose=PRINT_CHECKS):
    'returns true if path_ exists on the filesystem'
    path_ = normpath(path_)
    if verbose:
        pretty_path = path_ndir_split(path_, 2)
        caller_name = get_caller_name()
        logger.debug('[%s] checkpath(%r)', caller_name, pretty_path)
        if exists(path_):
            path_type = ''
            if isfile(path_):
                path_type += 'file'
            if isdir(path_):
                path_type += 'directory'
            if islink(path_):
                path_type += 'link'
            if ismount(path_):
                path_type += 'mount'
            path_type = 'file' if isfile(path_) else 'directory'
            logger.debug('(%s) exists', path_type)
        else:
            logger.debug('Path does not exist')
            if __CHECKPATH_VERBOSE__:
                logger.debug('[helpers] Path does not exist')
                _longest_path = longest_existing_path(path_)
                logger.debug(
                    '[helpers] Longest existing path: %r',
                    _longest_path,
                )
            return False
        return True
    else:
        return exists(path_)


def check_path(path_):
    return checkpath(path_)


def ensurepath(path_):
    if not checkpath(path_):
        logger.debug('[helpers] mkdir(%r)', path_)
        os.makedirs(path_)
    return True


def ensuredir(path_):
    return ensurepath(path_)


def ensure_path(path_):
    return ensurepath(path_)


def assertpath(path_):
    if not checkpath(path_):
        raise AssertionError('Asserted path does not exist: ' + path_)


def assert_path(path_):
    return assertpath(path_)


def join_mkdir(*args):
    'join and creates if not exists'
    output_dir = join(*args)
    if not exists(output_dir):
        logger.debug('Making dir: %s', output_dir)
        os.mkdir(output_dir)
    return output_dir


# ---File Copy---
def copy_task(cp_list, test=False, nooverwrite=False, print_tasks=True):
    '''
    Input list of tuples:
        format = [(src_1, dst_1), ..., (src_N, dst_N)]
    Copies all files src_i to dst_i
    '''
    num_overwrite = 0
    _cp_tasks = []  # Build this list with the actual tasks
    if nooverwrite:
        logger.debug('[helpers] Removed copy task')
    else:
        logger.debug('[helpers] Beginning copy and overwrite task')
    for (src, dst) in iter(cp_list):
        if exists(dst):
            num_overwrite += 1
            if print_tasks:
                logger.debug('[helpers] Overwriting %r', dst)
            if not nooverwrite:
                _cp_tasks.append((src, dst))
        else:
            if print_tasks:
                logger.debug('[helpers] Copying %r', src)
                _cp_tasks.append((src, dst))
        if print_tasks:
            logger.debug('[helpers] %s -> %s', src, dst)
    logger.debug('[helpers] About to copy %d files', len(cp_list))
    if nooverwrite:
        logger.debug('[helpers] Skipping %d overwrite tasks', num_overwrite)
    else:
        logger.debug('[helpers] There will be %d overwrites', num_overwrite)
    if not test:
        logger.debug('[helpers] Copying')
        for (src, dst) in iter(_cp_tasks):
            shutil.copy(src, dst)
        logger.debug('[helpers] Finished copying')
    else:
        logger.debug('[helpers] Test mode; nothing was copied')


def copy(src, dst):
    if exists(src):
        if exists(dst):
            prefix = 'C+O'
            logger.debug('[helpers] Copying and overwriting')
        else:
            prefix = 'C'
            logger.debug('[helpers] Copying')
        logger.debug('[%s] %s -> %s', prefix, src, dst)
        shutil.copy(src, dst)
    else:
        logger.warning(
            '[helpers] Cannot copy missing source %s to %s',
            src,
            dst,
        )


def copy_all(src_dir, dest_dir, glob_str_list, recursive=False):
    ensuredir(dest_dir)
    if not isinstance(glob_str_list, list):
        glob_str_list = [glob_str_list]
    for root, dirs, files in os.walk(src_dir):
        relative_root = relpath(root, src_dir)
        dest_root = (
            dest_dir
            if relative_root == os.curdir
            else join(dest_dir, relative_root)
        )
        for dname_ in dirs:
            for glob_str in glob_str_list:
                if fnmatch.fnmatch(dname_, glob_str):
                    dst = normpath(join(dest_root, dname_))
                    ensuredir(dst)
                    break
        for fname_ in files:
            for glob_str in glob_str_list:
                if fnmatch.fnmatch(fname_, glob_str):
                    src = normpath(join(root, fname_))
                    dst = normpath(join(dest_root, fname_))
                    ensuredir(split(dst)[0])
                    copy(src, dst)
                    break
        if not recursive:
            break


def copy_list(src_list, dst_list, lbl='Copying'):
    # Feb - 6 - 2014 Copy function
    def domove(src, dst, count):
        try:
            shutil.copy(src, dst)
        except OSError:
            return False
        mark_progress(count)
        return True
    task_iter = zip(src_list, dst_list)
    mark_progress, end_progress = progress_func(len(src_list), lbl=lbl)
    success_list = [domove(src, dst, count) for count, (src, dst) in enumerate(task_iter)]
    end_progress()
    return success_list


def move_list(src_list, dst_list, lbl='Moving'):
    # Feb - 6 - 2014 Move function
    def domove(src, dst, count):
        try:
            shutil.move(src, dst)
        except OSError:
            return False
        mark_progress(count)
        return True
    task_iter = zip(src_list, dst_list)
    mark_progress, end_progress = progress_func(len(src_list), lbl=lbl)
    success_list = [domove(src, dst, count) for count, (src, dst) in enumerate(task_iter)]
    end_progress()
    return success_list


# ---File / String Search----
def grep(string, pattern):
    if not isinstance(string, str):  # -> convert input to a string
        string = repr(string)
    matching_lines = []  # Find all matching lines
    for line in string.split('\n'):
        if not fnmatch.fnmatch(line, pattern):
            continue
        matching_lines.append(line)
    return matching_lines


def glob(dirname, pattern, recursive=False):
    matching_fnames = []
    for root, dirs, files in os.walk(dirname):
        for fname in files:
            if not fnmatch.fnmatch(fname, pattern):
                continue
            matching_fnames.append(join(root, fname))
        if not recursive:
            break
    return matching_fnames


def print_grep(*args, **kwargs):
    matching_lines = grep(*args, **kwargs)
    logger.debug("Matching Lines:\n    %s", '\n    '.join(matching_lines))


def print_glob(*args, **kwargs):
    matching_fnames = glob(*args, **kwargs)
    logger.debug("Matching Fnames:\n    %s", '\n    '.join(matching_fnames))


#---------------
# save / load / cache functions
def eval_from(fpath, err_onread=True):
    """Compatibility wrapper for :func:`hscom.serialization.eval_from`."""
    _serialization.VERY_VERBOSE = VERY_VERBOSE
    return _serialization.eval_from(fpath, err_onread=err_onread)


def read_from(fpath):
    """Compatibility wrapper for :func:`hscom.serialization.read_from`."""
    _serialization.VERY_VERBOSE = VERY_VERBOSE
    return _serialization.read_from(fpath)


def write_to(fpath, to_write):
    """Compatibility wrapper for :func:`hscom.serialization.write_to`."""
    _serialization.PRINT_WRITES = __PRINT_WRITES__
    return _serialization.write_to(fpath, to_write)


@DEPRECATED
def dict_union2(dict1, dict2):
    """Deprecated two-dictionary compatibility wrapper."""
    return dict(list(dict1.items()) + list(dict2.items()))


def dict_union(*args):
    return dict([item for dict_ in iter(args) for item in dict_.items()])


class ModulePrintLock():
    '''Temporarily turns off printing while still in scope
    chosen modules must have a print_off function
    '''
    def __init__(self, *args):
        self.module_list = args
        for module in self.module_list:
            module.print_off()

    def __del__(self):
        for module in self.module_list:
            module.print_on()

#def valid_filename_ascii_chars():
    ## Find invalid chars
    #ntfs_inval = '< > : " / \ | ? *'.split(' ')
    #other_inval = [' ', '\'', '.']
    ##case_inval = map(chr, range(97, 123))
    #case_inval = map(chr, range(65, 91))
    #invalid_chars = set(ntfs_inval + other_inval + case_inval)
    ## Find valid chars
    #valid_chars = []
    #for index in range(32, 127):
        #char = chr(index)
        #if not char in invalid_chars:
            #print index, chr(index)
            #valid_chars.append(chr(index))
    #return valid_chars
#valid_filename_ascii_chars()
# I Removed two characters that made awkward filenames
#ALPHABET = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9',  'a', 'b', 'c',
            #'d', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p',
            #'q', 'r', 's', 't', 'u', 'v', 'w', 'x', 'y', 'z', ';', '=', '@',
            #'[', ']', '^', '_', '`', '{', '}', '~', '!', '#', '$', '%', '&',
            #'(', ')', '+', ',', '-']
# --- Timing ---
def tic(msg=None):
    return (msg, time.time())


def toc(tt):
    (msg, start_time) = tt
    ellapsed = (time.time() - start_time)
    if not msg is None:
        logger.debug("...toc(%.4fs, %r)", ellapsed, str(msg))
    return ellapsed


# from http://stackoverflow.com/questions/6796492/python-temporarily-redirect-stdout-stderr
class RedirectStdout(object):
    def __init__(self, lbl=None, autostart=False, show_on_exit=True):
        self._stdout_old = sys.stdout
        self.stream = io.StringIO()
        self.record = '<no record>'
        self.lbl = lbl
        self.show_on_exit = show_on_exit
        if autostart:
            self.start()

    def start(self):
        sys.stdout.flush()
        sys.stdout = self.stream

    def stop(self):
        self.stream.flush()
        sys.stdout = self._stdout_old
        self.stream.seek(0)
        self.record = self.stream.read()
        return self.record

    def update(self):
        self.stop()
        self.dump()
        self.start()

    def dump(self):
        logger.debug("%s", indent(self.record, self.lbl))

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()
        if not self.lbl is None:
            if self.show_on_exit:
                self.dump()


class Indenter(RedirectStdout):
    def __init__(self, lbl='    '):
        super(Indenter, self).__init__(lbl=lbl, autostart=True)


class Indenter2(object):
    """Legacy indentation context.

    Older HotSpotter code monkey-patched every module-local ``print`` function
    while this context was active. Logging now owns formatting, so the context
    stays as a safe compatibility wrapper for decorators/call sites.
    """
    def __init__(self, lbl='    '):
        self.lbl = lbl

    def start(self):
        logger.debug("Entering indented context %s", self.lbl)

    def stop(self):
        logger.debug("Leaving indented context %s", self.lbl)

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.stop()

Indent = Indenter2


def rectify_wrapped_func(wrapper, func):
    wrapper.__name__ = func.__name__


def indent_decor(lbl):
    def indent_decor2(func):
        def indent_wrapper(*args, **kwargs):
            with Indenter2(lbl):
                ret = func(*args, **kwargs)
                return ret
        rectify_wrapped_func(indent_wrapper, func)
        return indent_wrapper
    return indent_decor2


class Timer(object):
    ''' Used to time statments with a with statment
    e.g with Timer() as t: some_function()'''
    def __init__(self, msg='', verbose=True, newline=True):
        self.msg = msg
        self.verbose = verbose
        self.newline = newline
        self.tstart = -1
        self.tic()

    def tic(self):
        if self.verbose:
            logger.debug("tic(%r)", self.msg)
            if self.newline:
                logger.debug("")
        self.tstart = time.time()

    def toc(self):
        ellapsed = (time.time() - self.tstart)
        if self.verbose:
            logger.debug("...toc(%r)=%.4fs", self.msg, ellapsed)
        return ellapsed

    def __enter__(self):
        #if not self.msg is None:
            #sys.stdout.write('---tic---'+self.msg+'  \n')
        #self.tic()
        pass

    def __exit__(self, type, value, trace):
        self.toc()


# --- Exec Strings ---
IPYTHON_EMBED_STR = r'''
try:
    import IPython
    print('Presenting in new ipython shell.')
    embedded = True
    IPython.embed()
except Exception as ex:
    printWARN(repr(ex)+'\n!!!!!!!!')
    embedded = False
'''


def ipython_execstr():
    return textwrap.dedent(r'''
    import matplotlib.pyplot as plt
    import sys
    embedded = False
    try:
        __IPYTHON__
        in_ipython = True
    except NameError:
        in_ipython = False
    try:
        import IPython
        have_ipython = True
    except NameError:
        have_ipython = False
    if in_ipython:
        print('Presenting in current ipython shell.')
    elif '--cmd' in sys.argv or 'devmode' in vars():
        print('[helpers] Requested IPython shell with --cmd argument.')
        if have_ipython:
            print('[helpers] Found IPython')
            try:
                import IPython
                print('[helpers] Presenting in new ipython shell.')
                embedded = True
                IPython.embed()
            except Exception as ex:
                print(repr(ex)+'\n!!!!!!!!')
                embedded = False
        else:
            print('[helpers] IPython is not installed')
    ''')


def execstr_dict(dict_, local_name, exclude_list=None):
    if exclude_list is None:
        execstr = '\n'.join((key + ' = ' + local_name + '[' + repr(key) + ']'
                            for (key, val) in dict_.items()))
    else:
        if not isinstance(exclude_list, list):
            exclude_list = [exclude_list]
        exec_list = []
        for (key, val) in dict_.items():
            if not any((fnmatch.fnmatch(key, pat) for pat in iter(exclude_list))):
                exec_list.append(key + ' = ' + local_name + '[' + repr(key) + ']')
        execstr = '\n'.join(exec_list)
    return execstr


def execstr_timeitsetup(dict_, exclude_list=None):
    '''
    Example:
    import timeit
    local_dict = locals().copy()
    exclude_list=['_*', 'In', 'Out', 'rchip1', 'rchip2']
    local_dict = locals().copy()
    setup = helpers.execstr_timeitsetup(local_dict, exclude_list)
    timeit.timeit('somefunc', setup)
    '''
    if exclude_list is None:
        exclude_list = []
    old_thresh =  np.get_printoptions()['threshold']
    np.set_printoptions(threshold=1000000000)
    matches = fnmatch.fnmatch
    excl_valid_keys = [key for key in dict_.keys() if not any((matches(key, pat) for pat in iter(exclude_list)))]
    valid_types = set([np.ndarray, np.float32, np.float64, np.int64, int, float])
    type_valid_keys = [key for key in iter(excl_valid_keys) if type(dict_[key]) in valid_types]
    exec_list = []
    for key in type_valid_keys:
        val = dict_[key]
        try:
            val_str = np.array_repr(val)
        except Exception:
            val_str = repr(val)  # NOQA
        exec_list.append(key + ' = ' + repr(dict_[key]))
    exec_str  = '\n'.join(exec_list)
    import_str = textwrap.dedent('''
    import numpy as np
    from numpy import array, float32, float64, int32, int64
    import helpers
    from spatial_verification2 import *
                                 ''')
    setup = import_str + exec_str
    np.set_printoptions(threshold=old_thresh)
    return setup


@DEPRECATED
def dict_execstr(dict_, local_name=None):
    return execstr_dict(dict_, local_name)


def execstr_func(func):
    logger.debug("Getting executable source for: %s", func.__name__)
    _src = inspect.getsource(func)
    execstr = textwrap.dedent(_src[_src.find(':') + 1:])
    # Remove return statments
    while True:
        stmtx = execstr.find('return')  # Find first 'return'
        if stmtx == -1:
            break  # Fail condition
        # The characters which might make a return not have its own line
        stmt_endx = len(execstr) - 1
        for stmt_break in '\n;':
            logger.debug("Executable source candidate:\n%s", execstr)
            logger.debug("Return statement offset: %d", stmtx)
            stmt_endx_new = execstr[stmtx:].find(stmt_break)
            if -1 < stmt_endx_new < stmt_endx:
                stmt_endx = stmt_endx_new
        # now have variables stmt_x, stmt_endx
        before = execstr[:stmtx]
        after  = execstr[stmt_endx:]
        execstr = before + after
    return execstr


@DEPRECATED
def execstr_src(func):
    """Deprecated executable-source helper; use ``inspect.getsource``."""
    return execstr_func(func)


@DEPRECATED
def get_exec_src(func):
    return execstr_func(func)


# --- Profiling ---
def unit_test(test_func):
    test_name = test_func.__name__

    def __unit_test_wraper():
        logger.debug("Testing: %s", test_name)
        try:
            ret = test_func()
        except Exception:
            logger.debug("Tested: %s ...FAILURE", test_name, exc_info=True)
            raise
        logger.debug("Tested: %s ...SUCCESS", test_name)
        return ret
    return __unit_test_wraper


@DEPRECATED
def runprofile(cmd, globals_=globals(), locals_=locals()):
    """Deprecated developer profiler that executes a command string."""
    # Meliae # from meliae import loader # om = loader.load('filename.json') # s = om.summarize();
    import cProfile
    import sys
    import os
    logger.debug("Profiling command: %s", cmd)
    cProfOut_fpath = 'OpenGLContext.profile'
    cProfile.runctx( cmd, globals_, locals_, filename=cProfOut_fpath)
    # RUN SNAKE
    logger.debug("Profiled output: %s", cProfOut_fpath)
    if sys.platform == 'win32':
        rsr_fpath = os.path.join(os.path.dirname(sys.executable),
                                 'Scripts', 'runsnake.exe')
    else:
        rsr_fpath = 'runsnake'
    view_cmd = rsr_fpath + ' "' + cProfOut_fpath + '"'
    os.system(view_cmd)
    return True

'''
def profile_lines(fname):
    import __init__
    script = 'dev.py'
    args = '--db MOTHERS --nocache-feat'
    runcmd = 'kernprof.py %s %s' % (script, args)
    viewcmd = 'python -m line_profiler %s.lprof' % script
    hs_path = split(__init__.__file__)
    lineprofile_path = join(hs_path, '.lineprofile')
    ensurepath(lineprofile_path)
    shutil.copy('*', lineprofile_path + '/*')
    '''


def memory_profile():
    #http://stackoverflow.com/questions/2629680/deciding-between-subprocess-multiprocessing-and-thread-in-python
    import guppy
    import gc
    logger.debug("Collecting garbage")
    gc.collect()
    hp = guppy.hpy()
    logger.debug("Waiting for heap output")
    heap_output = hp.heap()
    logger.debug("Heap output:\n%s", heap_output)
    # Graphical Browser
    #hp.pb()


def garbage_collect():
    import gc
    gc.collect()
#http://www.huyng.com/posts/python-performance-analysis/
#Once youve gotten your code setup with the @profile decorator, use kernprof.py to run your script.
#kernprof.py -l -v fib.py

#---------------
# printing and logging
#---------------

__STDOUT__ = sys.stdout
__STDERR__ = sys.stderr


def reset_streams():
    sys.stdout.flush()
    sys.stderr.flush()
    sys.stdout = __STDOUT__
    sys.stderr = __STDERR__
    sys.stdout.flush()
    sys.stderr.flush()
    logger.debug("Reset stdout and stderr")


def print_list(list):
    if list is None:
        return 'None'
    msg = '\n'.join([repr(item) for item in list])
    logger.debug("%s", msg)
    return msg


#def _print(msg):
    #sys.stdout.write(msg)


#def _println(msg):
    #sys.stdout.write(msg + '\n')


#def println(msg, *args):
    #args = args + tuple('\n',)
    #return print_(msg + ''.join(args))


#def flush():
    #sys.stdout.flush()
    #return ''


#def endl():
    #print_('\n')
    #sys.stdout.flush()
    #return '\n'


#def printINFO(msg, *args):
    #msg = 'INFO: ' + str(msg) + ''.join(map(str, args))
    #return println(msg, *args)


#def printERR(msg, *args):
    #msg = 'ERROR: ' + str(msg) + ''.join(map(str, args))
    #raise Exception(msg)
    #return println(msg, *args)


def printWARN(warn_msg, category=UserWarning):
    """Compatibility warning helper using logging as its sole channel.

    ``category`` remains accepted for callers of the historical API, but no
    Python warning is emitted.  This avoids reporting every event twice.
    """
    warn_msg = 'Probably not a big issue, but you should know...: ' + warn_msg
    logger.warning("%s", warn_msg)
    return warn_msg


#---------------
def try_cast(var, type_):
    if type_ is None:
        return var
    try:
        return type_(var)
    except Exception:
        return None


def get_arg(arg, type_=None, default=None):
    arg_after = default
    try:
        arg_index = sys.argv.index(arg)
        if arg_index < len(sys.argv):
            arg_after = try_cast(sys.argv[arg_index + 1], type_)
    except Exception:
        pass
    return arg_after


def get_flag(arg, default=False):
    'Checks if the commandline has a flag or a corresponding noflag'
    if arg.find('--') != 0:
        raise Exception(arg)
    #if arg.find('--no') == 0:
        #arg = arg.replace('--no', '--')
    noarg = arg.replace('--', '--no')
    if arg in sys.argv:
        return True
    elif noarg in sys.argv:
        return False
    else:
        return default
    return default


def listfind(list_, tofind):
    try:
        return list_.index(tofind)
    except ValueError:
        return None


def printshape(arr_name, locals_):
    arr = locals_[arr_name]
    if isinstance(arr, np.ndarray):
        logger.debug("%s.shape = %s", arr_name, arr.shape)
    else:
        logger.debug("len(%s) = %r", arr_name, len(arr))


def printvar2(varstr, attr=''):
    locals_ = get_parent_locals()
    printvar(locals_, varstr, attr)


class NpPrintOpts(object):
    def __init__(self, **kwargs):
        self.orig_opts = np.get_printoptions()
        self.new_opts = kwargs
    def __enter__(self):
        np.set_printoptions(**self.new_opts)
    def __exit__(self, type, value, trace):
        np.set_printoptions(**self.orig_opts)


def printvar(locals_, varname, attr='.shape'):
    from . import tools
    npprintopts = np.get_printoptions()
    np.set_printoptions(threshold=5)
    dotpos = varname.find('.')
    # Locate var
    if dotpos == -1:
        var = locals_[varname]
    else:
        varname_ = varname[:dotpos]
        dotname_ = varname[dotpos:]
        var_ = locals_[varname_]  # NOQA
        var = eval('var_' + dotname_)
    # Print in format
    typestr = tools.get_type(var)
    if isinstance(var, np.ndarray):
        varstr = eval('str(var' + attr + ')')
        logger.debug("[var] %s %s = %s", typestr, varname + attr, varstr)
    elif isinstance(var, list):
        if attr == '.shape':
            func = 'len'
        else:
            func = ''
        varstr = eval('str(' + func + '(var))')
        logger.debug("[var] %s len(%s) = %s", typestr, varname, varstr)
    else:
        logger.debug("[var] %s %s = %r", typestr, varname, var)
    np.set_printoptions(**npprintopts)


def save_testdata(*args, **kwargs):
    """Store trusted developer test data in a local pickle-backed shelf."""
    import shelve
    uid = kwargs.get('uid', '')
    shelf_fname = 'test_data_%s.shelf' % uid
    shelf = shelve.open(shelf_fname, protocol=pickle.HIGHEST_PROTOCOL)
    locals_ = get_parent_locals()
    for key in args:
        logger.debug("Stashing test-data key=%r", key)
        shelf[key] = locals_[key]
    shelf.close()


def load_testdata(*args, **kwargs):
    """Load trusted developer test data; never open an untrusted shelf."""
    import shelve
    uid = kwargs.get('uid', '')
    shelf_fname = 'test_data_%s.shelf' % uid
    shelf = shelve.open(shelf_fname)
    ret = [shelf[key] for key in args]
    shelf.close()
    if len(ret) == 1:
        ret = ret[0]
    return ret


@DEPRECATED
def import_testdata():
    """Import trusted developer shelf data into an interactive namespace."""
    from hscom import helpers as util
    import shelve
    shelf = shelve.open('test_data.shelf')
    logger.debug("Importing test-data keys:\n * %s",
                 '\n * '.join(list(shelf.keys())))
    shelf_exec = util.execstr_dict(shelf, 'shelf')
    exec(shelf_exec)
    shelf.close()
    return import_testdata.__code__.co_code


def num2_sigfig(num):
    return int(np.ceil(np.log10(num)))


def embed(parent_locals=None):
    if parent_locals is None:
        parent_locals = get_parent_locals()
    exec(execstr_dict(parent_locals, 'parent_locals'))
    logger.debug("Embedding IPython shell")
    import IPython
    IPython.embed()


def quitflag(num=None, embed_=False, parent_locals=None):
    if num is None or get_flag('--quit' + str(num)):
        if parent_locals is None:
            parent_locals = get_parent_locals()
        exec(execstr_dict(parent_locals, 'parent_locals'))
        if embed_:
            logger.debug("Triggered --quit%s", num)
            embed(parent_locals=parent_locals)
        logger.debug("Triggered --quit%s", num)
        sys.exit(1)


def qflag(num=None, embed_=True):
    return quitflag(num, embed_=embed_, parent_locals=get_parent_locals())


def quit(num=None, embed_=False):
    return quitflag(num, embed_=embed_, parent_locals=get_parent_locals())


def iflatten(list_):
    flat_iter = chain.from_iterable(list_)  # very fast flatten
    return flat_iter


def flatten(list_):
    return list(iflatten(list_))


def interleave(args):
    """Yield round-robin values until every input iterator is exhausted."""
    iterators = [iter(arg) for arg in args]
    while iterators:
        active_iterators = []
        for iterator in iterators:
            try:
                yield next(iterator)
            except StopIteration:
                continue
            active_iterators.append(iterator)
        iterators = active_iterators


# --- Context ---

def inIPython():
    try:
        __IPYTHON__
        return True
    except NameError:
        return False


def haveIPython():
    try:
        import IPython  # NOQA
        return True
    except (ImportError, ModuleNotFoundError):
        return False


def print_frame(frame):
    frame = frame if 'frame' in vars() else inspect.currentframe()
    attr_list = ['f_code.co_name', 'f_back', 'f_lineno',
                 'f_code.co_names', 'f_code.co_filename']
    for attr_path in attr_list:
        value = frame
        for attr in attr_path.split('.'):
            value = getattr(value, attr)
        logger.debug("frame.%s=%r", attr_path, value)
    local_varnames = pack_into('; '.join(list(frame.f_locals.keys())))
    logger.debug("%s", local_varnames)
    logger.debug("--- End Frame ---")


def search_stack_for_localvar(varname):
    curr_frame = inspect.currentframe()
    logger.debug("Searching parent frames for: %s", varname)
    frame_no = 0
    while not curr_frame.f_back is None:
        if varname in list(curr_frame.f_locals.keys()):
            logger.debug("Found in frame: %d", frame_no)
            return curr_frame.f_locals[varname]
        frame_no += 1
        curr_frame = curr_frame.f_back
    logger.debug("Found nothing in all %d frames", frame_no)
    return None


def get_parent_locals():
    this_frame = inspect.currentframe()
    call_frame = this_frame.f_back
    parent_frame = call_frame.f_back
    if parent_frame is None:
        return None
    return parent_frame.f_locals


def get_parent_globals():
    this_frame = inspect.currentframe()
    call_frame = this_frame.f_back
    parent_frame = call_frame.f_back
    if parent_frame is None:
        return None
    return parent_frame.f_globals


def get_caller_locals():
    this_frame = inspect.currentframe()
    call_frame = this_frame.f_back
    if call_frame is None:
        return None
    return call_frame.f_locals


def module_functions(module):
    module_members = inspect.getmembers(module)
    function_list = []
    for key, val in module_members:
        if inspect.isfunction(val) and inspect.getmodule(val) == module:
            function_list.append((key, val))
    return function_list


def public_attributes(input):
    public_attr_list = []
    all_attr_list = dir(input)
    for attr in all_attr_list:
        if attr.find('__') == 0:
            continue
        public_attr_list.append(attr)
    return public_attr_list


def explore_stack():
    stack = inspect.stack()
    tup = stack[0]
    for ix, tup in reversed(list(enumerate(stack))):
        frame = tup[0]
        logger.debug("--- Frame %2d: ---", ix)
        print_frame(frame)
        #next_frame = curr_frame.f_back


def explore_module(module_, seen=None, maxdepth=2, nonmodules=False):
    def __childiter(module):
        for aname in iter(dir(module)):
            if aname.find('_') == 0:
                continue
            try:
                yield module.__dict__[aname], aname
            except KeyError:
                logger.debug("Module attribute disappeared: %s", aname,
                             exc_info=True)
                pass

    def __explore_module(module, indent, seen, depth, maxdepth, nonmodules):
        valid_children = []
        ret = ''
        modname = str(module.__name__)
        #modname = repr(module)
        for child, aname in __childiter(module):
            try:
                if not isinstance(child, types.ModuleType):
                    if nonmodules:
                        #print_(depth)
                        fullstr = indent + '    ' + str(aname) + ' = ' + repr(child)
                        truncstr = truncate_str(fullstr) + '\n'
                        ret +=  truncstr
                    continue
                childname = str(child.__name__)
                if not seen is None:
                    if childname in seen:
                        continue
                    elif maxdepth is None:
                        seen.add(childname)
                if childname.find('_') == 0:
                    continue
                valid_children.append(child)
            except Exception:
                logger.debug("Could not inspect module child %s", aname,
                             exc_info=True)
                pass
        # Print
        # print_(depth)
        ret += indent + modname + '\n'
        # Recurse
        if not maxdepth is None and depth >= maxdepth:
            return ret
        ret += ''.join([__explore_module(child,
                                         indent + '    ',
                                         seen, depth + 1,
                                         maxdepth,
                                         nonmodules)
                       for child in iter(valid_children)])
        return ret
    #ret +=
    #print('#module = ' + str(module_))
    ret = __explore_module(module_, '     ', seen, 0, maxdepth, nonmodules)
    #print(ret)
    return ret


def debug_npstack(stacktup):
    logger.debug("Debugging numpy [hv]stack")
    logger.debug("len(stacktup) = %r", len(stacktup))
    for count, item in enumerate(stacktup):
        if isinstance(item, np.ndarray):
            logger.debug("item[%d].shape = %r", count, item.shape)
        elif isinstance(item, list) or isinstance(item, tuple):
            logger.debug("len(item[%d]) = %d", count, len(item))
            logger.debug("DEBUG LIST")
            with Indenter2(' * '):
                debug_list(item)
        else:
            logger.debug("type(item[%d]) = %r", count, type(item))


def debug_list(list_):
    dbgmessage = []
    append = dbgmessage.append
    append('debug_list')
    dim2 = None
    if all([is_listlike(item) for item in list_]):
        append(' * list items are all listlike')
        all_lens = [len(item) for item in list_]
        if list_eq(all_lens):
            dim2 = all_lens[0]
            append(' * uniform lens=%d' % dim2)
        else:
            append(' * nonuniform lens = %r' % np.unique(all_lens).tolist())
    else:
        all_types = [type(item) for item in list_]
        if list_eq(all_types):
            append(' * uniform types=%r' % all_types[0])
        else:
            append(' * nonuniform types: %r' % np.unique(all_types).tolist())
    logger.debug("%s", '\n'.join(dbgmessage))
    return dim2


def is_listlike(obj):
    return isinstance(obj, list) or isinstance(obj, tuple) or isinstance(obj, np.ndarray)


def debug_hstack(stacktup):
    try:
        return np.hstack(stacktup)
    except ValueError:
        logger.debug("ValueError in debug_hstack", exc_info=True)
        debug_npstack(stacktup)
        raise


def debug_vstack(stacktup):
    try:
        return np.vstack(stacktup)
    except ValueError:
        logger.debug("ValueError in debug_vstack", exc_info=True)
        debug_npstack(stacktup)
        raise
