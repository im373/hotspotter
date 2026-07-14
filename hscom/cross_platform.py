# HotSpotter port notes:
# Updated shared compatibility helpers for Python 3, NumPy 2, and Windows paths.
# Replaced hscom.__common__ hooks with logging/profiling/dev helpers.

'''
This module tries to ensure that the system paths are correctly setup for
hotspotter to run.
'''

import logging
import sys
from os.path import join, exists, normpath
import os
import subprocess
from .dev_utils import make_reloader

logger = logging.getLogger(__name__)
rrr = make_reloader(__name__, '[cplat]')
printDBG = logger.debug

# Macports python directories
ports_pyframework = '/opt/local/Library/Frameworks/Python.framework/Versions/3.11/'
ports_site_packages = join(ports_pyframework, 'lib/python3.11/site-packages/')


def ensure_pythonpath():
    if sys.platform == 'darwin':
        if exists(ports_pyframework) and not ports_pyframework in sys.path:
            sys.path.append(ports_site_packages)


def _cmd(*args, **kwargs):
    import shlex
    sys.stdout.flush()
    verbose = kwargs.get('verbose', True)
    detatch = kwargs.get('detatch', False)
    sudo = kwargs.get('sudo', False)
    if len(args) == 1 and isinstance(args[0], list):
        args = args[0]
    if isinstance(args, str):
        if os.name == 'posix':
            args = shlex.split(args)
        else:
            args = [args]
    if sudo is True and sys.platform != 'win32':
        args = ['sudo'] + args
    logger.info(f"Running command: {args!r}")
    PIPE = subprocess.PIPE
    proc = subprocess.Popen(args, stdout=PIPE, stderr=PIPE, shell=False)
    if detatch:
        return None, None, 1
    if verbose and not detatch:
        logged_list = []
        append = logged_list.append
        write = sys.stdout.write
        flush = sys.stdout.flush
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            write(line)
            flush()
            append(line)
        out = '\n'.join(logged_list)
        (out_, err) = proc.communicate()
        if err:
            logger.warning(f"Command stderr: {err!r}")
    else:
        # Surpress output
        (out, err) = proc.communicate()
    # Make sure process if finished
    ret = proc.wait()
    return out, err, ret


def startfile(fpath):
    logger.info(f"startfile({fpath!r})")
    if not exists(fpath):
        raise Exception('Cannot start nonexistant file: %r' % fpath)
    if sys.platform.startswith('linux'):
        out, err, ret = _cmd(['xdg-open', fpath], detatch=True)
        if not ret:
            raise Exception(out + ' -- ' + err)
    elif sys.platform.startswith('darwin'):
        out, err, ret = _cmd(['open', fpath], detatch=True)
        if not ret:
            raise Exception(out + ' -- ' + err)
    else:
        os.startfile(fpath)
    pass


def view_directory(dname=None):
    'view directory'
    logger.info(f"view_directory({dname!r})")
    dname = os.getcwd() if dname is None else dname
    open_prog = {'win32': 'explorer.exe',
                 'linux2': 'nautilus',
                 'darwin': 'open'}[sys.platform]
    os.system(open_prog + ' ' + normpath(dname))
