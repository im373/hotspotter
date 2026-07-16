#!/usr/bin/env python
"""Packaging metadata and maintenance commands for the Python 3 fork."""

from os.path import dirname, realpath, join, exists, normpath, expanduser, splitext
from pathlib import Path
import os
import subprocess
import sys
import fnmatch

from setuptools import find_packages
from setuptools import setup

ROOT = Path(__file__).resolve().parent
HOME = str(Path.home())

INSTALL_REQUIRES = [
    'numpy>=2.0',
    'scipy>=1.13',
    'Pillow>=10.0',
    'PyQt5>=5.15.9',
    'matplotlib>=3.8.4',
    'opencv-python>=4.10',
    'pylru>=1.2',
    'pyflann-ibeis>=2.3',
    'pyhesaff>=2.2',
]

# Imports used by the historical executable-builder configuration.
MODULES = [
    'PyQt5',
    'PyQt5.sip',
    'PyQt5.QtCore',
    'PyQt5.QtGui',
    'PyQt5.QtWidgets',
    'PIL.Image',
    'PIL.PngImagePlugin',
    'PIL.JpegImagePlugin',
    'PIL.GifImagePlugin',
    'PIL.PpmImagePlugin',
    'matplotlib',
    'numpy',
    'scipy',
    'cv2',
    'PIL',
]

INSTALL_OPTIONAL = [
    'networkx>=3.0',
    'parse>=1.20',
    'psutil>=5.9',
]

INSTALL_OTHER = [
    'ipython>=8.0',
]

INSTALL_BUILD = [
    'Cython>=3.0',
    'setuptools>=68',
    'wheel',
]

INSTALL_DEV = [
    'coverage>=7.0',
    'pyflakes>=3.0',
    'pylint>=3.0',
]

EXTRAS_REQUIRE = {
    'build': INSTALL_BUILD,
    'dev': INSTALL_DEV + INSTALL_OTHER + INSTALL_OPTIONAL,
    'tools': INSTALL_OTHER + INSTALL_OPTIONAL,
}

CLASSIFIERS = [
    'Development Status :: 3 - Alpha',
    'Intended Audience :: Developers',
    'Intended Audience :: Education',
    'Intended Audience :: Science/Research',
    'License :: OSI Approved :: Apache Software License',
    'Operating System :: MacOS',
    'Operating System :: Microsoft :: Windows',
    'Operating System :: POSIX :: Linux',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.11',
]
NAME = 'HotSpotter'
AUTHOR = 'Jonathan Crall, RPI'
AUTHOR_EMAIL = 'hotspotter.ir@gmail.com'
MAINTAINER = AUTHOR
MAINTAINER_EMAIL = AUTHOR_EMAIL
DESCRIPTION = 'Animal instance recognition and identification.'
LONG_DESCRIPTION = (ROOT / 'README.md').read_text(encoding='utf-8')
URL = 'https://github.com/Erotemic/hotspotter'
LICENSE = 'Apache-2.0'
PLATFORMS = ['Windows', 'Linux', 'macOS']
VERSION = '0.0.0.dev0'


def _cd(dpath, verbose=True):
    if verbose:
        print('[setup] change dir to: %r' % dpath)
    os.chdir(dpath)


def _cmd(args, verbose=True, sudo=False):
    sys.stdout.flush()
    if sudo and sys.platform != 'win32':
        if isinstance(args, str):
            args = 'sudo ' + args
        else:
            args = ['sudo'] + list(args)
    print('[setup] Running: %r' % args)
    completed = subprocess.run(
        args,
        capture_output=True,
        shell=isinstance(args, str),
        text=True,
    )
    if verbose:
        if completed.stdout:
            print(completed.stdout, end='')
        if completed.stderr:
            print(completed.stderr, end='', file=sys.stderr)
    return completed.stdout, completed.stderr, completed.returncode

if sys.platform == 'win32':
    buildscript_fmt = 'mingw_%s_build.bat'
else:
    buildscript_fmt = 'unix_%s_build.sh'


def clean():
    cwd = get_setup_dpath()
    print('[setup] Current working directory: %r' % cwd)
    # Remove python compiled files
    util.remove_files_in_dir(cwd, '*.pyc', recursive=True)
    util.remove_files_in_dir(cwd, '*.pyo', recursive=True)
    # Remove profile outputs
    util.remove_files_in_dir(cwd, '*.prof', recursive=True)
    util.remove_files_in_dir(cwd, '*.prof.txt', recursive=True)
    util.remove_files_in_dir(cwd, '*.lprof', recursive=True)
    # Remove cython generated c files carefully
    hsmod_list = ['hotspotter', 'hsgui', 'hsviz', 'hscom']
    for hsmod in hsmod_list:
        util.remove_files_in_dir(join(cwd, hsmod), '*.so', recursive=False)
        util.remove_files_in_dir(join(cwd, hsmod), '*.c', recursive=False)
        util.remove_files_in_dir(join(cwd, hsmod), '*.pyx', recursive=False)
    # Remove pyinstaller temp files
    clean_pyinstaller()
    # Remove latex temp files
    util.remove_files_in_dir(join(cwd, '_doc/user-guide-latex'), '*.synctex')
    util.remove_files_in_dir(join(cwd, '_doc/user-guide-latex'), '*.log')
    util.remove_files_in_dir(join(cwd, '_doc/user-guide-latex'), '*.out')
    util.remove_files_in_dir(join(cwd, '_doc/user-guide-latex'), '*.aux')
    # Remove logs
    util.remove_files_in_dir(join(cwd, 'logs'))
    # Remove misc
    util.delete(join(cwd, "'"))  # idk where this file comes from
    util.remove_files_in_dir(cwd + '/hstpl/extern_feat', 'libopencv_*.dylib', recursive=False)


def clean_pyinstaller():
    cwd = get_setup_dpath()
    util.remove_files_in_dir(cwd, 'HotSpotterApp.pkg', recursive=False)
    util.delete(join(cwd, 'dist'))
    util.delete(join(cwd, 'build'))


def build_pyinstaller():
    clean_pyinstaller()
    # Run the pyinstaller command (does all the work)
    _cmd('pyinstaller _setup/pyinstaller-hotspotter.spec')
    # Perform some post processing steps on the mac
    if sys.platform == 'darwin' and exists("dist/HotSpotter.app/Contents/"):
        copy_list = [
            ('hsicon.icns', 'Resources/icon-windowed.icns'),
            ('Info.plist', 'Info.plist'),
        ]
        srcdir = '_setup'
        dstdir = 'dist/HotSpotter.app/Contents/'
        for srcname, dstname in copy_list:
            src = join(srcdir, srcname)
            dst = join(dstdir, dstname)
            util.copy(src, dst)


def build_mac_dmg():
    _cmd('./_setup/mac_dmg_builder.sh')


def get_setup_dpath():
    assert exists('setup.py'), 'must be run in hotspotter directory'
    assert exists('../hotspotter/setup.py'), 'must be run in hotspotter directory'
    assert exists('../hotspotter/hotspotter'), 'must be run in hotspotter directory'
    assert exists('_setup'), 'must be run in hotspotter directory'
    cwd = normpath(realpath(dirname(__file__)))
    return cwd


def dbg_mac_otool():
    print('[setup] dbg_mac_otool()')
    import _setup.fix_lib_otool
    dpath = join(get_setup_dpath(), 'hstpl', 'extern_feat')
    filt_dylib = lambda path: fnmatch.fnmatch(path, '*.dylib')
    join_dylib = lambda path: join(dpath, path)
    dylib_list = map(join_dylib, filter(filt_dylib, os.listdir(dpath)))
    print('\n')
    for fpath in dylib_list:
        print('-----')
        _setup.fix_lib_otool.inspect_dylib(fpath)
        print('\n')
    print('\n')
    print('[setup] dylib_list: ')
    print(' * ' + '\n * '.join(dylib_list))


def fix_mac_otool():
    raise Exception('Error: do not use this. pyinstaller should take care of otool now')
    print('[setup] fix_mac_otool()')
    import _setup.fix_lib_otool
    dpath = join(get_setup_dpath(), 'hstpl', 'extern_feat')
    filt_dylib = lambda path: fnmatch.fnmatch(path, '*.dylib')
    join_dylib = lambda path: join(dpath, path)
    dylib_list = map(join_dylib, filter(filt_dylib, os.listdir(dpath)))
    needs_recurse = False
    for fpath in dylib_list:
        print('-----')
        if _setup.fix_lib_otool.make_distributable_dylib(fpath):
            needs_recurse = True
        print('\n')
    if needs_recurse:
        fix_mac_otool()


def build_win32_inno_installer():
    inno_dir = r'C:\Program Files (x86)\Inno Setup 5'
    inno_fname = 'ISCC.exe'
    inno_fpath = join(inno_dir, inno_fname)
    hsdir = get_setup_dpath()
    iss_script = join(hsdir, '_setup', 'wininstallerscript.iss')
    if not exists(inno_fpath):
        msg = '[setup] Inno not found and is needed for the win32 installer'
        print(msg)
        raise Exception(msg)
    args = [inno_fpath, iss_script]
    _cmd(args)
    import shutil
    installer_src = join(hsdir, '_setup', 'Output', 'hotspotter-win32-setup.exe')
    installer_dst = join(hsdir, 'dist', 'hotspotter-win32-setup.exe')
    shutil.move(installer_src, installer_dst)


def compile_ui():
    """Compile Qt Designer files using the repository's PyQt5 runtime."""
    widget_dir = join(dirname(realpath(__file__)), 'hsgui/_frontend')
    print('[setup] Compiling qt designer files in %r' % widget_dir)
    for widget_ui in util.glob(widget_dir, '*.ui'):
        widget_py = os.path.splitext(widget_ui)[0] + '.py'
        cmd = [
            sys.executable,
            '-m',
            'PyQt5.uic.pyuic',
            '-x',
            widget_ui,
            '-o',
            widget_py,
        ]
        print('[setup] compile_ui()>' + ' '.join(cmd))
        subprocess.check_call(cmd)


def fix_tpl_permissions():
    os.system('chmod +x hotspotter/_tpl/extern_feat/*.mac')
    os.system('chmod +x hotspotter/_tpl/extern_feat/*.ln')


def make_install_pyhesaff():
    dpath = normpath(HOME + '/code/hesaff')
    cmd = join(dpath, buildscript_fmt % 'hesaff')
    _cmd(cmd, sudo=True)


def make_install_pyflann():
    dpath = normpath(HOME + '/code/flann')
    cmd = join(dpath, buildscript_fmt % 'flann')
    _cmd(cmd, sudo=True)
    pass


def make_install_opencv():
    dpath = normpath(HOME + '/code/opencv')
    cmd = join(dpath, buildscript_fmt % 'opencv')
    _cmd(cmd, sudo=True)
    pass


def inrepo(func):
    # Decorator. I forgot what it does. Something with
    # repository paths.
    def wrapper(repo, *args, **kwargs):
        repo_dpath = join(expanduser('~'), 'code', repo)
        cwd = os.getcwd()
        _cd(repo_dpath, False)
        result = func(repo, *args, **kwargs)
        _cd(cwd, False)
        print('')
        return result
    return wrapper


@inrepo
def pull(repo, branch=''):
    if repo == 'hotspotter':
        _cmd('git pull hyrule ' + branch)
        _cmd('git pull github ' + branch)
    else:
        _cmd('git pull ' + branch)


@inrepo
def push(repo):
    if repo == 'hotspotter':
        _cmd('git push origin')
        _cmd('git push github')
    else:
        _cmd('git push')


@inrepo
def status(repo):
    print('[setup] ---- status(%r) ----' % repo)
    with util.Indenter('[%s]' % repo):
        _cmd('git status')


def compile_cython(fpath):
    """Build one Cython extension in place for the active Python runtime."""
    from Cython.Build import cythonize
    from setuptools import Extension
    from setuptools.dist import Distribution

    fname, _ = splitext(fpath)
    if exists(fname + '.pyx'):
        fpath = fname + '.pyx'
    module_name = fname.replace('\\', '.').replace('/', '.')
    extensions = cythonize(
        [Extension(module_name, [fpath])],
        compiler_directives={'language_level': 3},
    )
    distribution = Distribution({'ext_modules': extensions})
    command = distribution.get_command_obj('build_ext')
    command.inplace = True
    command.ensure_finalized()
    command.run()
    return 0


def inspect_cython_typness(fpath):
    from hscom import cross_platform as cplat
    _cmd('cython -a ' + fpath)
    html_fpath = splitext(fpath)[0] + '.html'
    cplat.startfile(html_fpath)


def build_cython():
    # Sorted roughly by importance (how slow the module is)
    # Critical Section
    compile_cython('hotspotter/spatial_verification2.py')
    #compile_cython('hotspotter/matching_functions.py')
    compile_cython('hotspotter/nn_filters.py')
    compile_cython('hotspotter/algos.py')
    #compile_cython('hotspotter/match_chips3.py')

    # Cannot cython this file
    #compile_cython('hstpl/extern_feat/pyhesaff.py')

    #compile_cython('hsviz/draw_func2.py')
    #compile_cython('hsviz/viz.py')
    #compile_cython('hsviz/interact.py')

    #
    compile_cython('hscom/__common__.py')
    compile_cython('hscom/Parallelize.py')
    compile_cython('hscom/fileio.py')
    compile_cython('hscom/tools.py')
    compile_cython('hscom/Printable.py')
    compile_cython('hscom/Preferences.py')

    compile_cython('hotspotter/chip_compute2.py')
    compile_cython('hotspotter/feature_compute2.py')
    compile_cython('hotspotter/extern_feat.py')
    compile_cython('hotspotter/load_data2.py')

    compile_cython('hotspotter/Config.py')
    compile_cython('hotspotter/QueryResult.py')
    compile_cython('hotspotter/voting_rules2.py')
    compile_cython('hotspotter/segmentation.py')
    compile_cython('hotspotter/report_results2.py')

    compile_cython('hotspotter/DataStructures.py')
    compile_cython('hotspotter/HotSpotterAPI.py')


def build_pyo():
    paths = ['.', 'hotspotter', 'hsgui', 'hsviz', 'hscom', 'hstpl/extern_feat']
    subprocess.check_call([
        sys.executable,
        '-O',
        '-m',
        'compileall',
        '-q',
    ] + paths)


SETUP_KWARGS = {
    'name': NAME,
    'version': VERSION,
    'description': DESCRIPTION,
    'long_description': LONG_DESCRIPTION,
    'long_description_content_type': 'text/markdown',
    'url': URL,
    'project_urls': {
        'Source': URL,
        'Issue Tracker': URL + '/issues',
    },
    'author': AUTHOR,
    'author_email': AUTHOR_EMAIL,
    'maintainer': MAINTAINER,
    'maintainer_email': MAINTAINER_EMAIL,
    'license': LICENSE,
    'license_files': ('LICENSE.txt',),
    'platforms': PLATFORMS,
    'classifiers': CLASSIFIERS,
    'python_requires': '>=3.11',
    'packages': find_packages(exclude=('hstest', 'hstest.*')),
    'py_modules': ['main'],
    'include_package_data': True,
    'package_data': {'hsgui._frontend': ['*.ui']},
    'install_requires': INSTALL_REQUIRES,
    'extras_require': EXTRAS_REQUIRE,
    'entry_points': {
        'console_scripts': ['hotspotter=main:main'],
    },
    'zip_safe': False,
}


CUSTOM_COMMANDS = {
    'clean',
    'buildui', 'ui', 'compile_ui',
    'o', 'pyo',
    'c', 'cython',
    'installer', 'pyinstaller', 'build_pyinstaller', 'build_installer',
    'inno', 'win32inno',
    'dmg', 'macdmg',
    'otool', 'dbg-otool',
    'flann', 'pyflann',
    'hesaff', 'pyhesaff',
    'opencv',
    'pull', 'status', 'push', 'update',
}


def run_custom_commands(commands):
    """Run retained repository-maintenance commands outside setuptools."""
    global util
    from hscom import helpers as util

    print('[setup] Entering HotSpotter setup')
    for cmd in commands:
        # Clean up non-source files
        if cmd in ['clean']:
            clean()
        # Build PyQt UI files
        if cmd in ['buildui', 'ui', 'compile_ui']:
            compile_ui()

        # Build optimized files
        if cmd in ['o', 'pyo']:
            build_pyo()

        if cmd in ['c', 'cython']:
            build_cython()

        # Build distributable executable
        if cmd in ['installer', 'pyinstaller', 'build_pyinstaller', 'build_installer']:
            build_pyinstaller()

        # Package into windows installer
        if cmd in ['inno', 'win32inno']:
            build_win32_inno_installer()
        # Package into mac installer
        if cmd in ['dmg', 'macdmg']:
            build_mac_dmg()

        # Debug tools
        if cmd in ['otool']:
            fix_mac_otool()
        if cmd in ['dbg-otool']:
            dbg_mac_otool()

        # Build depenencies
        if cmd in ['flann', 'pyflann']:
            make_install_pyflann()
        if cmd in ['hesaff', 'pyhesaff']:
            make_install_pyhesaff()
        if cmd in ['opencv']:
            make_install_opencv()

        # Git commands
        if cmd in ['pull']:
            pull('opencv')
            pull('hesaff')
            pull('flann')
            pull('hotspotter')
        if cmd in ['status']:
            status('opencv')
            status('hesaff')
            status('flann')
            status('hotspotter')
        if cmd in ['push']:
            #push('opencv')
            #push('hesaff')
            #push('flann')
            push('hotspotter')

        if cmd in ['update']:
            pull('opencv', 'hsbranch248')
            pull('hesaff', 'hotspotter_hesaff')
            pull('flann', 'hotspotter_flann')
            pull('hotspotter', 'jon')


if __name__ == '__main__':
    custom_commands = [
        command for command in sys.argv[1:]
        if command in CUSTOM_COMMANDS
    ]
    if custom_commands:
        run_custom_commands(custom_commands)
    else:
        setup(**SETUP_KWARGS)
