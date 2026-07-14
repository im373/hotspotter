# HotSpotter port notes:
# Updated Qt dialogs, slots, and matplotlib interaction helpers for PyQt5.
# Added logging-friendly orientation/ROI interaction behavior.
# Replaced hscom.__common__ logging hooks with module-level logging.

# Python
import builtins
import logging
import math
from os.path import split
import sys
# Science
import numpy as np
# Qt
from PyQt5 import QtCore
from PyQt5 import QtWidgets

# HotSpotter
from hscom import fileio as io
from hscom import helpers
from hscom import helpers as util
from hsviz import draw_func2 as df2

logger = logging.getLogger(__name__)
profile = getattr(builtins, 'profile', lambda func: func)

IS_INIT = False
QAPP = None
IS_ROOT = False
DISABLE_NODRAW = False
DEBUG = False

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s


def configure_matplotlib():
    import multiprocessing
    import matplotlib
    mplbackend = matplotlib.get_backend()
    if multiprocessing.current_process().name == 'MainProcess':
        logger.info(f"Current matplotlib backend is {mplbackend!r}")
        logger.info("Switching matplotlib backend to Qt5Agg")
    else:
        return
    matplotlib.rcParams['toolbar'] = 'toolbar2'
    matplotlib.rc('text', usetex=False)
    #matplotlib.rcParams['text'].usetex = False
    if mplbackend != 'Qt5Agg':
        matplotlib.use('Qt5Agg', force=True)
        mplbackend = matplotlib.get_backend()
        if multiprocessing.current_process().name == 'MainProcess':
            logger.info(f"Current matplotlib backend is {mplbackend!r}")
        #matplotlib.rcParams['toolbar'] = 'None'
        #matplotlib.rcParams['interactive'] = True


#---------------
# SLOT DECORATORS
#---------------


def slot_(*types, **kwargs_):  # This is called at wrap time to get args
    '''
    wrapper around pyqtslot decorator
    *args = types
    kwargs_['initdbg']
    kwargs_['rundbg']
    '''
    initdbg = kwargs_.get('initdbg', DEBUG)
    rundbg  = kwargs_.get('rundbg', DEBUG)

    # Wrap with debug statments
    def pyqtSlotWrapper(func):
        func_name = func.__name__
        if initdbg:
            logger.debug(f"Wrapping {func.__name__!r} with slot_")

        if rundbg:
            @QtCore.pyqtSlot(*types, name=func.__name__)
            def slot_wrapper(self, *args, **kwargs):
                argstr_list = list(map(str, args))
                kwastr_list = ['%s=%s' % item for item in kwargs.items()]
                argstr = ', '.join(argstr_list + kwastr_list)
                logger.debug(f"Begin slot {func_name}({argstr})")
                #with helpers.Indenter():
                result = func(self, *args, **kwargs)
                logger.debug(f"Finished slot {func_name}({argstr})")
                return result
        else:
            @QtCore.pyqtSlot(*types, name=func.__name__)
            def slot_wrapper(self, *args, **kwargs):
                result = func(self, *args, **kwargs)
                return result

        slot_wrapper.__name__ = func_name
        return slot_wrapper
    return pyqtSlotWrapper


#/SLOT DECORATOR
#---------------


# BLOCKING DECORATOR
# TODO: This decorator has to be specific to either front or back. Is there a
# way to make it more general?
def backblocking(func):
    #printDBG('[@guitools] Wrapping %r with backblocking' % func.func_name)

    def block_wrapper(back, *args, **kwargs):
        #print('[guitools] BLOCKING')
        wasBlocked_ = back.front.blockSignals(True)
        try:
            result = func(back, *args, **kwargs)
        except Exception as ex:
            back.front.blockSignals(wasBlocked_)
            logger.exception(f"Block wrapper caught exception in {func.__name__!r}")
            logger.debug(f"back = {back!r}")
            VERBOSE = False
            if VERBOSE:
                logger.debug(f"*args = {args!r}")
                logger.debug(f"**kwargs = {kwargs!r}")
            #print('ex = %r' % ex)
            #back.user_info('Error in blocking ex=%r' % ex)
            back.user_info('Error while blocking gui:\nex=%r' % ex)
            raise
        back.front.blockSignals(wasBlocked_)
        #print('[guitools] UNBLOCKING')
        return result
    block_wrapper.__name__ = func.__name__
    return block_wrapper


def frontblocking(func):
    # HACK: blocking2 is specific to fron
    #printDBG('[@guitools] Wrapping %r with frontblocking' % func.func_name)

    def block_wrapper(front, *args, **kwargs):
        #print('[guitools] BLOCKING')
        #wasBlocked = self.blockSignals(True)
        wasBlocked_ = front.blockSignals(True)
        try:
            result = func(front, *args, **kwargs)
        except Exception as ex:
            front.blockSignals(wasBlocked_)
            logger.exception(f"Block wrapper caught exception in {func.__name__!r}")
            logger.debug(f"front = {front!r}")
            VERBOSE = False
            if VERBOSE:
                logger.debug(f"*args = {args!r}")
                logger.debug(f"**kwargs = {kwargs!r}")
            #print('ex = %r' % ex)
            front.user_info('Error in blocking ex=%r' % ex)
            raise
        front.blockSignals(wasBlocked_)
        #print('[guitools] UNBLOCKING')
        return result
    block_wrapper.__name__ = func.__name__
    return block_wrapper


# DRAWING DECORATOR
def drawing(func):
    'Wraps a class function and draws windows on completion'
    #printDBG('[@guitools] Wrapping %r with drawing' % func.func_name)
    @util.indent_decor('[drawing]')
    def drawing_wrapper(self, *args, **kwargs):
        #print('[guitools] DRAWING')
        result = func(self, *args, **kwargs)
        #print('[guitools] DONE DRAWING')
        if kwargs.get('dodraw', True) or DISABLE_NODRAW:
            df2.draw()
        return result
    drawing_wrapper.__name__ = func.__name__
    return drawing_wrapper


@profile
def select_orientation():
    #from matplotlib.backend_bases import mplDeprecation
    logger.info("Define an orientation angle by clicking two points")
    fig = None
    oldcbfn = None
    try:
        # Compute an angle from user interaction
        sys.stdout.flush()
        fig = df2.gcf()
        oldcbid, oldcbfn = df2.disconnect_callback(fig, 'button_press_event')
        fig.canvas.draw_idle()
        logger.info("Waiting for 2 points from ginput")
        pts = np.asarray(fig.ginput(2))
        logger.info(f"ginput returned pts={pts!r}")
        # if len(pts) != 2:
        #     print('[*guitools] orientation selection cancelled: pts=%r' % (pts,))
        #     return None
        refpt = pts[1] - pts[0]
        theta = math.atan2(refpt[1], refpt[0])
        logger.info(f"Calculated theta={theta!r} refpt={refpt!r}")
        return theta
    except Exception as ex:
        logger.exception(f"Annotate Orientation Failed {ex!r}")
        return None
    finally:
        if fig is not None:
            df2.connect_callback(fig, 'button_press_event', oldcbfn)


@profile
def select_roi(initial_roi=None, theta=0):
    if initial_roi is not None:
        return select_roi_drag(initial_roi, theta=theta)
    #from matplotlib.backend_bases import mplDeprecation
    logger.info("Define a rectangular ROI by clicking two points")
    fig = None
    oldcbfn = None
    try:
        sys.stdout.flush()
        fig = df2.gcf()
        # Disconnect any other button_press events
        oldcbid, oldcbfn = df2.disconnect_callback(fig, 'button_press_event')
        fig.canvas.draw_idle()
        pts = fig.ginput(2)
        logger.info(f"ginput(2) = {pts!r}")
        if len(pts) != 2:
            logger.info(f"ROI selection cancelled: pts={pts!r}")
            return None
        [(x1, y1), (x2, y2)] = pts
        xm = min(x1, x2)
        xM = max(x1, x2)
        ym = min(y1, y2)
        yM = max(y1, y2)
        xywh = list(map(int, list(map(round, (xm, ym, xM - xm, yM - ym)))))
        roi = np.array(xywh, dtype=np.int32)
        logger.info(f"Selected ROI = {roi!r}")
        return roi
    except Exception as ex:
        logger.exception(f"ROI selection failed: {ex!r}")
        return None
    finally:
        if fig is not None:
            df2.connect_callback(fig, 'button_press_event', oldcbfn)

## new reselect

def _rotmat(theta):
    cos_ = math.cos(theta)
    sin_ = math.sin(theta)
    return np.array([[cos_, -sin_], [sin_, cos_]], dtype=np.float64)


def _roi_corners(roi, theta):
    x, y, w, h = np.asarray(roi, dtype=np.float64)
    center = np.array([x + w / 2.0, y + h / 2.0], dtype=np.float64)
    local = np.array([[-w / 2.0, -h / 2.0],
                      [ w / 2.0, -h / 2.0],
                      [ w / 2.0,  h / 2.0],
                      [-w / 2.0,  h / 2.0]], dtype=np.float64)
    return center + local.dot(_rotmat(theta).T)


def _roi_from_dragged_corner(anchor, dragged, theta):
    rot = _rotmat(theta)
    # draw_roi maps local rectangle points to image data as local.dot(rot.T).
    # Project data points with dot(rot) so the dragged mouse position becomes
    # the actual post-rotation corner after the ROI is redrawn.
    anchor_local = np.asarray(anchor, dtype=np.float64).dot(rot)
    dragged_local = np.asarray(dragged, dtype=np.float64).dot(rot)
    min_xy = np.minimum(anchor_local, dragged_local)
    max_xy = np.maximum(anchor_local, dragged_local)
    local_center = (min_xy + max_xy) / 2.0
    width, height = max_xy - min_xy
    width = max(width, 1.0)
    height = max(height, 1.0)
    center = local_center.dot(rot.T)
    roi = np.array([center[0] - width / 2.0,
                    center[1] - height / 2.0,
                    width,
                    height])
    return np.array(np.round(roi), dtype=np.int32)


@profile
def select_roi_drag(initial_roi, theta=0):
    logger.info("Adjust ROI by dragging one of its corner handles")
    fig = None
    ax = None
    oldcbfn = None
    callback_ids = []
    artists = []
    state = {
        'active_corner': None,
        'anchor': None,
        'roi': np.asarray(initial_roi, dtype=np.int32).copy(),
        'done': False,
        'cancelled': False,
    }

    def clear_artists():
        while artists:
            artist = artists.pop()
            try:
                artist.remove()
            except ValueError:
                pass

    def draw_handles():
        clear_artists()
        corners = _roi_corners(state['roi'], theta)
        closed = np.vstack([corners, corners[0]])
        line, = ax.plot(closed[:, 0], closed[:, 1], color='yellow',
                        linewidth=2, zorder=20)
        handles = ax.scatter(corners[:, 0], corners[:, 1], s=80,
                             c='yellow', edgecolors='black', zorder=21)
        artists.extend([line, handles])
        fig.canvas.draw_idle()

    def nearest_corner(event):
        corners = _roi_corners(state['roi'], theta)
        display_pts = ax.transData.transform(corners)
        mouse = np.array([event.x, event.y], dtype=np.float64)
        dists = np.linalg.norm(display_pts - mouse, axis=1)
        corner = int(np.argmin(dists))
        return corner if dists[corner] <= 25 else None

    def on_press(event):
        if event.inaxes is not ax or event.xdata is None or event.ydata is None:
            return
        if event.button != 1:
            state['cancelled'] = True
            state['done'] = True
            fig.canvas.stop_event_loop()
            return
        corner = nearest_corner(event)
        if corner is None:
            logger.info("Click closer to a yellow ROI corner handle")
            return
        state['active_corner'] = corner
        state['anchor'] = _roi_corners(state['roi'], theta)[(corner + 2) % 4]

    def on_motion(event):
        if state['active_corner'] is None:
            return
        if event.inaxes is not ax or event.xdata is None or event.ydata is None:
            return
        dragged = np.array([event.xdata, event.ydata], dtype=np.float64)
        state['roi'] = _roi_from_dragged_corner(state['anchor'], dragged, theta)
        draw_handles()

    def on_release(event):
        if state['active_corner'] is None:
            return
        state['active_corner'] = None
        state['done'] = True
        logger.info(f"Selected ROI = {state['roi']!r}")
        fig.canvas.stop_event_loop()

    try:
        sys.stdout.flush()
        fig = df2.gcf()
        ax = df2.gca()
        oldcbid, oldcbfn = df2.disconnect_callback(fig, 'button_press_event')
        draw_handles()
        callback_ids = [
            fig.canvas.mpl_connect('button_press_event', on_press),
            fig.canvas.mpl_connect('motion_notify_event', on_motion),
            fig.canvas.mpl_connect('button_release_event', on_release),
        ]
        logger.info("Drag a yellow ROI corner; right-click cancels")
        fig.canvas.start_event_loop(timeout=0)
        if state['cancelled']:
            logger.info("ROI drag selection cancelled")
            return None
        return state['roi']
    except Exception as ex:
        logger.exception(f"ROI drag selection failed: {ex!r}")
        return None
    finally:
        if fig is not None:
            for callback_id in callback_ids:
                fig.canvas.mpl_disconnect(callback_id)
            clear_artists()
            df2.connect_callback(fig, 'button_press_event', oldcbfn)
            fig.canvas.draw_idle()


def _addOptions(msgBox, options):
    #msgBox.addButton(QtWidgets.QMessageBox.Close)
    for opt in options:
        role = QtWidgets.QMessageBox.ApplyRole
        msgBox.addButton(QtWidgets.QPushButton(opt), role)


def _cacheReply(msgBox):
    dontPrompt = QtWidgets.QCheckBox('dont ask me again', parent=msgBox)
    dontPrompt.blockSignals(True)
    msgBox.addButton(dontPrompt, QtWidgets.QMessageBox.ActionRole)
    return dontPrompt


def _newMsgBox(msg='', title='', parent=None, options=None, cache_reply=False):
    msgBox = QtWidgets.QMessageBox(parent)
    #msgBox.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    #std_buts = QtWidgets.QMessageBox.Close
    #std_buts = QtWidgets.QMessageBox.NoButton
    std_buts = QtWidgets.QMessageBox.Cancel
    msgBox.setStandardButtons(std_buts)
    msgBox.setWindowTitle(title)
    msgBox.setText(msg)
    msgBox.setModal(parent is not None)
    return msgBox


@profile
def msgbox(msg, title='msgbox'):
    'Make a non modal critical QtWidgets.QMessageBox.'
    msgBox = QtWidgets.QMessageBox(None)
    msgBox.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msgBox.setWindowTitle(title)
    msgBox.setText(msg)
    msgBox.setModal(False)
    msgBox.open(msgBox.close)
    msgBox.show()
    return msgBox


def user_input(parent, msg, title='input dialog'):
    reply, ok = QtWidgets.QInputDialog.getText(parent, title, msg)
    if not ok:
        return None
    return str(reply)


def user_info(parent, msg, title='info'):
    msgBox = _newMsgBox(msg, title, parent)
    msgBox.setAttribute(QtCore.Qt.WA_DeleteOnClose)
    msgBox.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msgBox.setModal(False)
    msgBox.open(msgBox.close)
    msgBox.show()


@profile
def _user_option(parent, msg, title='options', options=['No', 'Yes'], use_cache=False):
    'Prompts user with several options with ability to save decision'
    logger.debug(f"User option prompt title={title!r} msg={msg!r}")
    # Recall decision
    logger.debug(f"Asking user: {msg!r} {title!r}")
    cache_id = helpers.hashstr(title + msg)
    if use_cache:
        reply = io.global_cache_read(cache_id, default=None)
        if reply is not None:
            return reply
    # Create message box
    msgBox = _newMsgBox(msg, title, parent)
    _addOptions(msgBox, options)
    if use_cache:
        dontPrompt = _cacheReply(msgBox)
    # Wait for output
    optx = msgBox.exec_()
    if optx == QtWidgets.QMessageBox.Cancel:
        return None
    try:
        reply = options[optx]
    except Exception as ex:
        logger.exception("User option selection failed")
        logger.debug(f"optx = {optx!r}")
        logger.debug(f"options = {options!r}")
        logger.debug(f"ex = {ex!r}")
        raise
    # Remember decision
    if use_cache and dontPrompt.isChecked():
        io.global_cache_write(cache_id, reply)
    del msgBox
    return reply


def user_question(msg):
    msgBox = QtWidgets.QMessageBox.question(None, '', 'lovely day?')
    return msgBox


def getQtImageNameFilter():
    imgNamePat = ' '.join(['*' + ext for ext in helpers.IMG_EXTENSIONS])
    imgNameFilter = 'Images (%s)' % (imgNamePat)
    return imgNameFilter


@profile
def select_images(caption='Select images:', directory=None):
    name_filter = getQtImageNameFilter()
    selected = select_files(caption, directory, name_filter)
    logger.info(f"Selected images = {selected!r}")
    return selected


@profile
def select_files(caption='Select Files:', directory=None, name_filter=None):
    'Selects one or more files from disk using a qt dialog'
    logger.info(f"{caption}")
    if directory is None:
        directory = io.global_cache_read('select_directory')
    qdlg = QtWidgets.QFileDialog()
    qfile_list = qdlg.getOpenFileNames(caption=caption, directory=directory, filter=name_filter)
    logger.debug(f"qfile_list = {qfile_list!r}")
    if isinstance(qfile_list, tuple):
        qfile_list = qfile_list[0]
    if isinstance(qfile_list, str):
        file_list = [qfile_list]
    else:
        file_list = [str(fpath) for fpath in qfile_list]
    logger.info(f"Selected {len(file_list)} files")
    io.global_cache_write('select_directory', directory)
    return file_list


@profile
def select_directory(caption='Select Directory', directory=None):
    logger.info(f"{caption}")
    if directory is None:
        directory = io.global_cache_read('select_directory')
    qdlg = QtWidgets.QFileDialog()
    qopt = QtWidgets.QFileDialog.ShowDirsOnly
    qdlg_kwargs = dict(caption=caption, options=qopt, directory=directory)
    dpath = str(qdlg.getExistingDirectory(**qdlg_kwargs))
    logger.info(f"Selected directory: {dpath!r}")
    io.global_cache_write('select_directory', split(dpath)[0])
    return dpath


@profile
def show_open_db_dlg(parent=None):
    # OLD
    from ._frontend import OpenDatabaseDialog
    if not '-nc' in sys.argv and not '--nocache' in sys.argv:
        db_dir = io.global_cache_read('db_dir')
        if db_dir == '.':
            db_dir = None
    logger.debug(f"Cached db_dir={db_dir!r}")
    if parent is None:
        parent = QtWidgets.QDialog()
    opendb_ui = OpenDatabaseDialog.Ui_Dialog()
    opendb_ui.setupUi(parent)
    #opendb_ui.new_db_but.clicked.connect(create_new_database)
    #opendb_ui.open_db_but.clicked.connect(open_old_database)
    parent.show()
    return opendb_ui, parent


@util.indent_decor('[qt-init]')
@profile
def init_qtapp():
    global IS_INIT
    global IS_ROOT
    global QAPP
    if QAPP is not None:
        return QAPP, IS_ROOT
    app = QtCore.QCoreApplication.instance()
    is_root = app is None
    if is_root:  # if not in qtconsole
        logger.info("Initializing QApplication")
        app = QtWidgets.QApplication(sys.argv)
        QAPP = app
    try:
        __IPYTHON__
        is_root = False
    # You are not root if you are in IPYTHON
    except NameError:
        pass
    IS_INIT = True
    return app, is_root


@util.indent_decor('[qt-exit]')
@profile
def exit_application():
    logger.info("Exiting application")
    QtWidgets.qApp.quit()


@util.indent_decor('[qt-main]')
@profile
def run_main_loop(app, is_root=True, back=None, **kwargs):
    if back is not None:
        logger.debug("Setting active window")
        app.setActiveWindow(back.front)
        back.timer = ping_python_interpreter(**kwargs)
    if is_root:
        exec_core_app_loop(app)
        #exec_core_event_loop(app)
    else:
        logger.debug("Using root main loop")


@profile
def exec_core_event_loop(app):
    # This works but does not allow IPython injection
    logger.info("Running core application loop")
    try:
        from IPython.lib.inputhook import enable_qt5
        enable_qt5()
        from IPython.lib.guisupport import start_event_loop_qt5
        logger.info("Starting IPython Qt5 hook")
        start_event_loop_qt5(app)
    except ImportError:
        pass
    app.exec_()


@profile
def exec_core_app_loop(app):
    # This works but does not allow IPython injection
    logger.info("Running core application loop")
    app.exec_()
    #sys.exit(app.exec_())


@profile
def ping_python_interpreter(frequency=4200):  # 4200):
    'Create a QTimer which lets the python catch ctrl+c'
    timer = QtCore.QTimer()
    timer.timeout.connect(lambda: None)
    timer.start(frequency)
    return timer


def make_dummy_main_window():
    class DummyBackend(QtCore.QObject):
        def __init__(self):
            super(DummyBackend,  self).__init__()
            self.front = QtWidgets.QMainWindow()
            self.front.setWindowTitle('Dummy Main Window')
            self.front.show()
    back = DummyBackend()
    return back


def get_scope(qobj, scope_title='_scope_list'):
    if not hasattr(qobj, scope_title):
        setattr(qobj, scope_title, [])
    return getattr(qobj, scope_title)


def clear_scope(qobj, scope_title='_scope_list'):
    setattr(qobj, scope_title, [])


def enfore_scope(qobj, scoped_obj, scope_title='_scope_list'):
    get_scope(qobj, scope_title).append(scoped_obj)


@profile
def popup_menu(widget, opt2_callback, parent=None):
    def popup_slot(pos):
        logger.debug(f"Popup menu position: {pos!r}")
        menu = QtWidgets.QMenu()
        actions = [menu.addAction(opt, func) for opt, func in
                   iter(opt2_callback)]
        #pos=QtWidgets.QCursor.pos()
        selection = menu.exec_(widget.mapToGlobal(pos))
        return selection, actions
    if parent is not None:
        # Make sure popup_slot does not lose scope.
        for _slot in get_scope(parent, '_popup_scope'):
            parent.customContextMenuRequested.disconnect(_slot)
        clear_scope(parent, '_popup_scope')
        parent.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        parent.customContextMenuRequested.connect(popup_slot)
        enfore_scope(parent, popup_slot, '_popup_scope')
    return popup_slot


@profile
def make_header_lists(tbl_headers, editable_list, prop_keys=[]):
    col_headers = tbl_headers[:] + prop_keys
    col_editable = [False] * len(tbl_headers) + [True] * len(prop_keys)
    for header in editable_list:
        col_editable[col_headers.index(header)] = True
    return col_headers, col_editable
