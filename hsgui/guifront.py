# HotSpotter port notes:
# Converted frontend signals/widgets to PyQt5 namespace imports.
# Centralized table display tweaks such as chip/name column widths.
# Moved menu action creation/wiring out of generated MainSkel.
# Loaded menu action source strings from hsgui.menu_strings for Qt translation.
# Replaced hscom.__common__ logging hooks with module-level logging.

import logging
from os.path import exists, join
import sys
# Qt
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

# HotSpotter
from ._frontend.MainSkel import Ui_mainSkel
from ._frontend.TableFilterDialog import TableFilterDialog
from . import guitools
from . import menu_strings
from .guitools import slot_
from .guitools import frontblocking as blocking
from hscom import tools

logger = logging.getLogger(__name__)


def _translate(context, text):
    return QtWidgets.QApplication.translate(context, text)


def translate_menu_text(key):
    return _translate(menu_strings.MENU_CONTEXT, menu_strings.text(key))


def translate_menu_tooltip(key):
    tooltip = menu_strings.tooltip(key)
    return None if tooltip is None else _translate(menu_strings.MENU_CONTEXT, tooltip)

#=================
# Globals
#=================

IS_INIT = False
NOSTEAL_OVERRIDE = False  # Hard disable switch for stream stealer

TABLE_COLUMN_WIDTH_FACTORS = {
    'cxs': {'Name': 2.0},
    'nxs': {'Name': 2.0},
}

TABLE_TAB_LABELS = {
    'gxs': 'Image Table',
    'cxs': 'Chip Table',
    'nxs': 'Name Table',
    'res': 'Query Results Table',
}


#=================
# Decorators / Helpers
#=================

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

def clicked(func):
    def clicked_wrapper(front, item, *args, **kwargs):
        if front.isItemEditable(item):
            logger.debug("Ignoring click on editable column")
            return
        if item == front.prev_tbl_item:
            return
        front.prev_tbl_item = item
        return func(front, item, *args, **kwargs)
    clicked_wrapper.__name__ = func.__name__
    # Hacky decorator
    return clicked_wrapper


def csv_sanatize(str_):
    return str(str_).replace(',', ';;')


def apply_table_column_widths(tblname, tbl, col_fancyheaders):
    """Apply per-table display width preferences after headers are created."""
    width_factors = TABLE_COLUMN_WIDTH_FACTORS.get(tblname, {})
    if not width_factors:
        return
    default_width = tbl.horizontalHeader().defaultSectionSize()
    for header, factor in width_factors.items():
        if header in col_fancyheaders:
            col = col_fancyheaders.index(header)
            tbl.horizontalHeader().resizeSection(col, int(default_width * factor))


#=================
# Stream Stealer
#=================


class GUILoggingSender(QtCore.QObject):
    write_ = QtCore.pyqtSignal(str)

    def __init__(self, front):
        super(GUILoggingSender, self).__init__()
        self.write_.connect(front.gui_write)

    def write_gui(self, msg):
        self.write_.emit(str(msg))


class GUILoggingHandler(logging.StreamHandler):
    """
    A handler class which sends messages to to a connected QSlot
    """
    def __init__(self, front):
        super(GUILoggingHandler, self).__init__()
        self.sender = GUILoggingSender(front)

    def emit(self, record):
        try:
            msg = self.format(record) + '\n'
            self.sender.write_.emit(msg)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


def add_gui_logging_handler(handler):
    formatter = logging.Formatter(
        '%(asctime)s %(levelname)-8s %(name)s: %(message)s',
        '%H:%M:%S',
    )
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)


class StreamStealer(QtCore.QObject):
    write_ = QtCore.pyqtSignal(str)
    flush_ =  QtCore.pyqtSignal()

    def __init__(self, front, parent=None, share=False):
        super(StreamStealer, self).__init__(parent)
        # Define the Stream Stealer write function
        if share:
            self.write = self.write_shared
        else:
            self.write = self.write_gui
        self.write_.connect(front.gui_write)
        self.flush_.connect(front.gui_flush)
        # Do the stealing
        #stream_holder = sys
        #try:
            #__IPYTHON__
            #print('[front] detected __IPYTHON__')
            #from IPython.utils import io as iio
            #stream_holder = iio.IOTerm(None, self)
            #return
        #except NameError:
            #print('[front] did not detect __IPYTHON__')
            #pass
        #except Exception as ex:
            #print(ex)
            #raise

        # Remember which stream you've stolen
        self.iostream = sys.stdout
        self.iostream2 = sys.stderr
        # Redirect standard out to the StreamStealer object
        sys.stderr = self
        sys.stdout = self
        #steam_holder.stdout

    def write_shared(self, msg):
        msg_ = str(str(msg))
        self.iostream.write(msg_)
        self.write_.emit(msg_)

    def write_gui(self, msg):
        self.write_.emit(str(msg))

    def flush(self):
        self.flush_.emit()


def _steal_stdout(front):
    from hscom import params
    #front.ui.outputEdit.setPlainText(sys.stdout)
    nosteal = params.args.nosteal
    noshare = params.args.noshare
    if '--cmd' in sys.argv:
        nosteal = noshare = True
    #from IPython.utils import io
    #with io.capture_output() as captured:
        #%run my_script.py
    if NOSTEAL_OVERRIDE or (nosteal and noshare):
        logger.debug("Not stealing stdout")
        return
    logger.debug("Stealing standard out")
    if front.ostream is None:
        # Connect a StreamStealer object to the GUI output window
        if '--nologging' in sys.argv:
            front.ostream = StreamStealer(front, share=not noshare)
        else:
            front.gui_logging_handler = GUILoggingHandler(front)
            add_gui_logging_handler(front.gui_logging_handler)
    else:
        logger.debug("Stream already stolen")


def _return_stdout(front):
    #front.ui.outputEdit.setPlainText(sys.stdout)
    logger.debug("Returning standard out")
    if front.ostream is not None:
        sys.stdout = front.ostream.iostream
        sys.stderr = front.ostream.iostream2
        front.ostream = None
        return True
    else:
        logger.debug("Stream has not been stolen")
        return False

#=================
# Menus
#=================

def action_spec(action_name, i18n_key, slot_fn=None, shortcut=None, enabled=True):
    return {
        'name': action_name,
        'i18n_key': i18n_key,
        'slot_fn': slot_fn,
        'shortcut': shortcut,
        'enabled': enabled,
    }


def menu_action_specs(front):
    back = front.backend
    return {
        'menuFile': [
            action_spec('actionNew_Database', 'new_database', front.new_database, 'Ctrl+N'),
            action_spec('actionOpen_Database', 'open_database', front.open_database, 'Ctrl+O'),
            None,
            action_spec('actionSave_Database', 'save_database', back.save_database, 'Ctrl+S'),
            None,
            action_spec('actionImport_Img_file', 'import_img_file', front.import_images_from_file, 'Ctrl+I'),
            action_spec('actionImport_Img_dir', 'import_img_dir', front.import_images_from_dir),
            None,
            action_spec('actionQuit', 'quit', front.quit_application),
        ],
        'menuView': [
            action_spec('actionLayout_Figures', 'layout_figures', front.layout_figures, 'Ctrl+L'),
            None,
            action_spec('actionFilter_Table', 'filter_table', front.filter_table, 'Ctrl+F'),
        ],
        'menuActions': [
            action_spec('actionAdd_Chip', 'add_chip', front.add_chip, 'A'),
            action_spec('actionNew_Chip_Property', 'new_chip_property', front.new_prop),
            None,
            action_spec('actionQuery', 'query', back.query, 'Q'),
            None,
            action_spec('actionReselect_ROI', 'reselect_roi', front.reselect_roi, 'R'),
            action_spec('actionReselect_Ori', 'reselect_ori', front.reselect_ori, 'O'),
            None,
            action_spec('actionNext', 'next', back.select_next, 'N'),
            action_spec('actionNext_Unannotated', 'next_unannotated', back.select_next_unannotated, 'Shift+N'),
            None,
            action_spec('actionDelete_Chip', 'delete_chip', back.delete_chip, 'Ctrl+Del'),
            action_spec('actionDelete_Image', 'delete_image', back.delete_image, 'Ctrl+Shift+Del'),
        ],
        'menuBatch': [
            action_spec('actionPrecomputeChipsFeatures', 'precompute_chips_features', back.precompute_feats, 'Ctrl+Return'),
            action_spec('actionPrecompute_Queries', 'precompute_queries', back.precompute_queries),
            None,
            action_spec('actionScale_all_ROIS', 'scale_all_rois', None, enabled=False),
            None,
            action_spec('actionConvert_all_images_into_chips', 'convert_all_images_into_chips', None, enabled=False),
        ],
        'menuOptions': [
            action_spec('actionPreferences', 'preferences', front.edit_preferences, 'Ctrl+P'),
        ],
        'menuHelp': [
            action_spec('actionAbout', 'about', lambda: guitools.msgbox('About', 'hotspotter'),  enabled=False),
            action_spec('actionView_Docs', 'view_docs', back.view_docs),
            None,
            action_spec('actionView_DBDir', 'view_dbdir', back.view_database_dir),
            action_spec('actionView_Computed_Dir', 'view_computed_dir', back.view_computed_dir),
            action_spec('actionView_Global_Dir', 'view_global_dir',  back.view_global_dir),
            None,
            action_spec('actionWriteLogs', 'write_logs', None, enabled=False),
            None,
            action_spec('actionDelete_Precomputed_Results', 'delete_precomputed_results', back.delete_queryresults_dir),
            action_spec('actionDelete_computed_directory', 'delete_computed_directory', front.delete_cache),
            action_spec('actionDelete_global_preferences', 'delete_global_preferences', back.delete_global_prefs),
            None,
            action_spec('actionDev_Mode_IPython', 'dev_mode_ipython', front.dev_mode, 'Ctrl+Alt+Shift+D'),
            action_spec('actionDeveloper_Reload', 'developer_reload', front.dev_reload, 'Ctrl+Shift+R'),
            action_spec('actionDetect_Duplicate_Images', 'detect_duplicate_images', back.detect_dupimg),
        ],
    }


def new_menu_action(front, menu_name, name, text=None, shortcut=None,
                    tooltip=None, slot_fn=None, enabled=True):
    # Dynamically add new menu actions programatically
    action_name = name
    action_text = text
    action_shortcut = shortcut
    ui = front.ui
    if hasattr(ui, action_name):
        raise Exception('menu action already defined')
    action = QtWidgets.QAction(front)
    setattr(ui, action_name, action)
    action.setShortcutContext(QtCore.Qt.ApplicationShortcut)
    action.setObjectName(_fromUtf8(action_name))
    action.setEnabled(enabled)
    menu = getattr(ui, menu_name)
    menu.addAction(action)
    if action_text is None:
        action_text = action_name
    action.setText(action_text)
    if action_shortcut is not None:
        action.setShortcut(action_shortcut)
    if tooltip is not None:
        action.setToolTip(tooltip)
    if slot_fn is not None:
        action.triggered.connect(slot_fn)
    return action


def add_menu_separator(front, menu_name):
    menu = getattr(front.ui, menu_name)
    menu.addSeparator()


def create_menu_actions(front):
    for menu_name, specs in menu_action_specs(front).items():
        for spec in specs:
            if spec is None:
                add_menu_separator(front, menu_name)
                continue
            i18n_key = spec['i18n_key']
            new_menu_action(front, menu_name, spec['name'],
                            text=translate_menu_text(i18n_key),
                            shortcut=spec.get('shortcut'),
                            tooltip=translate_menu_tooltip(i18n_key),
                            slot_fn=spec.get('slot_fn'),
                            enabled=spec.get('enabled', True))

#=================
# Initialization
#=================


def init_ui(front):
    ui = Ui_mainSkel()
    ui.setupUi(front)
    return ui


def make_main_window(app=None, hs=None):
    """Construct the backend and frontend with a one-way dependency."""
    from hscom import params
    from . import guiback

    backend = guiback.MainWindowBackend(hs=hs)
    frontend = MainWindowFrontend(backend=backend)
    if app is not None:
        app._hotspotter_main_window = frontend
        app.setActiveWindow(frontend)

    nogui = bool(getattr(getattr(params, 'args', None), 'nogui', False))
    if hs is not None:
        backend.connect_api(hs)
    if hs is None or not nogui:
        frontend.show()
        if hs is None:
            frontend.layout_figures()
    return backend, frontend


#def popup(front, pos):
    #for i in front.ui.gxs_TBL.selectionModel().selection().indexes():
        #print(repr((i.row(), i.column())))
    #menu = QtWidgets.QMenu()
    #action1 = menu.addAction("action1")
    #action2 = menu.addAction("action2")
    #action3 = menu.addAction("action2")
    #action = menu.exec_(front.ui.gxs_TBL.mapToGlobal(pos))
    #print('action = %r ' % action)


class MainWindowFrontend(QtWidgets.QMainWindow):
    printSignal     = QtCore.pyqtSignal(str)
    quitSignal      = QtCore.pyqtSignal()
    selectGxSignal  = QtCore.pyqtSignal(int)
    selectCidSignal = QtCore.pyqtSignal(int)
    selectResSignal = QtCore.pyqtSignal(int)
    selectNameSignal = QtCore.pyqtSignal(str)
    changeCidSignal = QtCore.pyqtSignal(int, str, str)
    aliasNameSignal = QtCore.pyqtSignal(int, str, str)
    changeGxSignal  = QtCore.pyqtSignal(int, str, bool)
    querySignal = QtCore.pyqtSignal()

    def __init__(front, backend, parent=None):
        super(MainWindowFrontend, front).__init__(parent)
        front.prev_tbl_item = None
        front.ostream = None
        front.gui_logging_handler = None
        front.backend = backend
        front._backend_block_stack = []
        front.edit_prefs = None
        front.ui = init_ui(front)
        create_menu_actions(front)
        # Progress bar is not hooked up yet
        front.ui.progressBar.setVisible(False)
        front.connect_signals()
        front.steal_stdout()
        from hsviz import draw_func2 as df2
        df2.register_qt_win(front)

    def steal_stdout(front):
        return _steal_stdout(front)

    def return_stdout(front):
        return _return_stdout(front)

    @slot_(bool)
    def set_backend_busy(front, busy):
        if busy:
            front._backend_block_stack.append(front.blockSignals(True))
        elif front._backend_block_stack:
            was_blocked = front._backend_block_stack.pop()
            front.blockSignals(was_blocked)

    @slot_(str, str)
    def show_information(front, title, message):
        guitools.user_info(front, message, title=title)

    @slot_(str, str)
    def show_error(front, title, message):
        QtWidgets.QMessageBox.critical(front, title, message)

    @slot_()
    def handle_api_connected(front):
        from hscom import params

        if not bool(getattr(getattr(params, 'args', None), 'nogui', False)):
            front.layout_figures()

    @slot_()
    def quit_application(front):
        guitools.exit_application()

    @slot_()
    @blocking
    def new_database(front):
        while True:
            new_db = guitools.user_input(
                front,
                'Enter the new database name',
                title='New Database',
            )
            if not new_db:
                logger.info("Aborted new database creation")
                return

            reply = guitools._user_option(
                front,
                'Where should I put %r?' % new_db,
                'New Database',
                ['Choose Directory', 'My Work Dir'],
                True,
            )
            if reply == 'My Work Dir':
                put_dir = front.backend.get_work_directory()
            elif reply == 'Choose Directory':
                put_dir = guitools.select_directory(
                    'Select where to put the new database',
                    parent=front,
                )
            else:
                logger.info("Aborted new database creation")
                return

            if not put_dir or not exists(put_dir):
                error = 'Directory %r does not exist.' % put_dir
            else:
                new_dbdir = join(put_dir, new_db)
                error = None
            if error is None and exists(new_dbdir):
                error = 'New DB %r already exists.' % new_dbdir
            elif error is None:
                front.backend.new_database(new_dbdir)
                return

            retry = guitools._user_option(
                front,
                error,
                'New Database Failed',
                ['Try Again'],
                False,
            )
            if retry != 'Try Again':
                return

    @slot_()
    @blocking
    def open_database(front):
        db_dir = guitools.select_directory(
            'Select (or create) a database directory.',
            parent=front,
        )
        if db_dir:
            front.backend.open_database(db_dir)

    @slot_()
    @blocking
    def import_images_from_file(front):
        fpath_list = guitools.select_images(
            'Select image files to import',
            parent=front,
        )
        if fpath_list:
            front.backend.import_images_from_file(fpath_list)

    @slot_()
    @blocking
    def import_images_from_dir(front):
        img_dpath = guitools.select_directory(
            'Select directory with images in it',
            parent=front,
        )
        if img_dpath:
            front.backend.import_images_from_dir(img_dpath)

    @slot_()
    @blocking
    def new_prop(front):
        newprop = guitools.user_input(
            front,
            'What is the new property name?',
            title='New Chip Property',
        )
        if newprop:
            front.backend.new_prop(newprop)

    @slot_()
    @blocking
    def add_chip(front):
        gx = front.backend.get_selected_gx()
        if gx is None:
            front.show_information(
                'Add Chip', 'Select an image before adding a chip')
            return
        front.backend.show_image(
            gx,
            figtitle='Image View - Select ROI (click two points)',
        )
        roi = guitools.select_roi()
        if roi is not None:
            front.backend.add_chip(gx, roi)

    @slot_()
    @blocking
    def reselect_roi(front):
        context = front.backend.get_selected_chip_context()
        if context is None:
            front.show_information(
                'Reselect ROI', 'Cannot reselect ROI. No chip selected')
            return
        front.backend.show_image(
            context['gx'],
            [context['cx']],
            figtitle='Image View - ReSelect ROI (drag a yellow corner)',
        )
        roi = guitools.select_roi(
            context['roi'],
            theta=context['theta'],
        )
        if roi is not None:
            front.backend.reselect_roi(roi=roi)

    @slot_()
    @blocking
    def reselect_ori(front):
        context = front.backend.get_selected_chip_context()
        if context is None:
            front.show_information(
                'Reselect Orientation',
                'Cannot reselect orientation. No chip selected',
            )
            return
        front.backend.show_image(
            context['gx'],
            [context['cx']],
            figtitle='Image View - Select Orientation (click two points)',
        )
        theta = guitools.select_orientation()
        if theta is not None:
            front.backend.reselect_ori(theta=theta)

    @slot_()
    def edit_preferences(front):
        preferences = front.backend.get_preferences()
        front.edit_prefs = front.show_preferences(
            preferences,
            front.backend.default_preferences,
        )
        query_uid = ''.join(preferences.query_cfg.get_uid())
        logger.debug("query_uid = %s", query_uid)

    @slot_()
    def delete_cache(front):
        answer = guitools._user_option(
            front,
            'Are you sure you want to delete cache?',
            options=['No', 'Yes'],
        )
        if answer == 'Yes':
            front.backend.delete_cache()

    @slot_()
    @blocking
    def dev_mode(front):
        from hscom import helpers as util

        steal_again = front.return_stdout()
        hs = front.backend.get_hotspotter()  # NOQA
        back = front.backend  # NOQA
        devmode = True  # NOQA
        logger.info("Finished developer help setup")
        QtCore.pyqtRemoveInputHook()
        execstr = util.ipython_execstr()
        logger.warning(
            "Debugging in IPython. IPython will break gui until you exit")
        exec(execstr)
        if steal_again:
            front.steal_stdout()

    @slot_()
    @blocking
    def dev_reload(front):
        from hsdev import dev_reload
        from hsviz import draw_func2 as df2

        dev_reload.reload_all_modules()
        df2.unregister_qt_win('all')
        df2.register_qt_win(front)
        front.backend.populate_tables()

    def show_preferences(front, preferences, default_callback):
        widget = preferences.createQWidget()
        widget.ui.defaultPrefsBUT.clicked.connect(default_callback)
        return widget

    @slot_()
    @blocking
    def layout_figures(front):
        from hsviz import draw_func2 as df2

        logger.debug("Layout figures")
        app = QtWidgets.QApplication.instance()
        if app is None:
            logger.warning("Cannot detect screen geometry")
            diagonal = 1618
        else:
            screen_rect = app.desktop().screenGeometry()
            width = screen_rect.width()
            height = screen_rect.height()
            diagonal = (width ** 2 + height ** 2) ** 0.5 / 1.618
        df2.present(num_rc=(2, 3), wh=diagonal, wh_off=(0, 60))


    @slot_()
    def closeEvent(front, event):
        event.accept()
        front.quitSignal.emit()

    def connect_signals(front):
        # Connect signals to slots
        back = front.backend
        ui = front.ui
        # Frontend Signals
        front.printSignal.connect(back.backend_print)
        front.quitSignal.connect(front.quit_application)
        front.selectGxSignal.connect(back.select_gx)
        front.selectCidSignal.connect(back.select_cid)
        front.selectResSignal.connect(back.select_res_cid)
        front.selectNameSignal.connect(back.select_name)
        front.changeCidSignal.connect(back.change_chip_property)
        front.aliasNameSignal.connect(back.alias_name)
        front.changeGxSignal.connect(back.change_image_property)
        front.querySignal.connect(back.query)

        # Backend Signals
        back.populateSignal.connect(front.populate_tbl)
        back.setEnabledSignal.connect(front.setEnabled)
        back.windowTitleSignal.connect(front.setWindowTitle)
        back.busySignal.connect(front.set_backend_busy)
        back.informationSignal.connect(front.show_information)
        back.operationFailedSignal.connect(front.show_error)
        back.apiConnectedSignal.connect(front.handle_api_connected)

        # Gui Components
        # Tables Widgets
        ui.cxs_TBL.itemClicked.connect(front.chip_tbl_clicked)
        ui.cxs_TBL.itemChanged.connect(front.chip_tbl_changed)
        ui.gxs_TBL.itemClicked.connect(front.img_tbl_clicked)
        ui.gxs_TBL.itemChanged.connect(front.img_tbl_changed)
        ui.res_TBL.itemClicked.connect(front.res_tbl_clicked)
        ui.res_TBL.itemChanged.connect(front.res_tbl_changed)
        ui.nxs_TBL.itemClicked.connect(front.name_tbl_clicked)
        ui.nxs_TBL.itemChanged.connect(front.name_tbl_changed)
        # Tab Widget
        ui.tablesTabWidget.currentChanged.connect(front.change_view)
        ui.cxs_TBL.sortByColumn(0, QtCore.Qt.AscendingOrder)
        ui.res_TBL.sortByColumn(0, QtCore.Qt.AscendingOrder)
        ui.gxs_TBL.sortByColumn(0, QtCore.Qt.AscendingOrder)

    @slot_(bool)
    def setEnabled(front, flag):
        #front.printDBG('setEnabled(%r)' % flag)
        ui = front.ui
        # Enable or disable all actions
        for uikey in list(ui.__dict__.keys()):
            if uikey.find('action') == 0:
                ui.__dict__[uikey].setEnabled(flag)

        # The following options are always enabled
        always_enabled = [
            'actionOpen_Database',
            'actionNew_Database',
            'actionQuit',
            'actionAbout',
            'actionView_Docs',
            'actionDelete_global_preferences',
        ]
        for action_name in always_enabled:
            if hasattr(ui, action_name):
                getattr(ui, action_name).setEnabled(True)

        # The following options are no implemented. Disable them
        disabled_actions = [
            'actionConvert_all_images_into_chips',
            'actionScale_all_ROIS',
            'actionWriteLogs',
            'actionAbout',
        ]
        for action_name in disabled_actions:
            if hasattr(ui, action_name):
                getattr(ui, action_name).setEnabled(False)
        #ui.actionView_Docs.setEnabled(False)

    @slot_(str, list, list, list, list)
    @blocking
    def populate_tbl(front, tblname, col_fancyheaders, col_editable, row_list, datatup_list):
        tblname = str(tblname)
        tbl_dict = {
            'gxs': front.ui.gxs_TBL,
            'cxs': front.ui.cxs_TBL,
            'nxs': front.ui.nxs_TBL,
            'res': front.ui.res_TBL,
        }
        tbl = tbl_dict[tblname]

        front._populate_table(
            tblname,
            tbl,
            col_fancyheaders,
            col_editable,
            row_list,
            datatup_list,
        )

        # Set the tab text to show the number of items listed
        tablename2_tabwidget = {
            'gxs': front.ui.image_view,
            'cxs': front.ui.chip_view,
            'nxs': front.ui.name_view,
            'res': front.ui.result_view,
        }
        ui = front.ui
        tab_widget = tablename2_tabwidget[tblname]
        tab_index = ui.tablesTabWidget.indexOf(tab_widget)
        tab_text = _translate(
            "mainSkel",
            "%s (%d)" % (TABLE_TAB_LABELS[tblname], len(row_list)),
        )
        ui.tablesTabWidget.setTabText(tab_index, tab_text)

    def current_table(front):
        current_widget = front.ui.tablesTabWidget.currentWidget()
        widget_tables = [
            (front.ui.image_view, 'gxs', front.ui.gxs_TBL),
            (front.ui.chip_view, 'cxs', front.ui.cxs_TBL),
            (front.ui.name_view, 'nxs', front.ui.nxs_TBL),
            (front.ui.result_view, 'res', front.ui.res_TBL),
        ]
        for widget, tblname, table in widget_tables:
            if current_widget is widget:
                return tblname, table
        raise RuntimeError('The selected tab does not contain a known table')

    @slot_()
    def filter_table(front):
        tblname, tbl = front.current_table()
        headers = [
            str(tbl.horizontalHeaderItem(column).text())
            for column in range(tbl.columnCount())
            if tbl.horizontalHeaderItem(column) is not None
        ]
        if not headers:
            logger.warning("[filter] There is no columns to filter in table %s.", tblname)
            QtWidgets.QMessageBox.information(
                front,
                _translate('TableFilterDialog', 'Filter Table'),
                _translate(
                    'TableFilterDialog',
                    'The current table has no columns to filter.',
                ),
            )
            return

        conditions = front.backend.get_table_filters(tblname, headers)
        while True:
            dialog = TableFilterDialog(headers, conditions, front)
            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                return
            conditions = dialog.conditions()
            try:
                front.backend.set_table_filters(tblname, headers, conditions)
            except ValueError as ex:
                QtWidgets.QMessageBox.warning(
                    front,
                    _translate('TableFilterDialog', 'Invalid Table Filter'),
                    str(ex),
                )
                continue
            return

    def _populate_table(front, tblname, tbl, col_fancyheaders, col_editable, row_list, datatup_list):
        # TODO: for chip table: delete metedata column
        # RCOS TODO:
        # I have a small right-click context menu working
        # Maybe one of you can put some useful functions in these?
        # RCOS TODO: How do we get the clicked item on a right click?
        # RCOS TODO:
        # The data tables should not use the item model
        # Instead they should use the more efficient and powerful QAbstractItemModel / QAbstractTreeModel
        def set_header_context_menu(hheader):
            hheader.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            opt2_callback = [
                ('header', lambda: logger.debug("finishme")),
                ('cancel', lambda: logger.debug("cancel")), ]
            popup_slot = guitools.popup_menu(tbl, opt2_callback)
            hheader.customContextMenuRequested.connect(popup_slot)

        def set_table_context_menu(tbl):
            tbl.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            opt2_callback = [
                ('Query', front.querySignal.emit), ]
            popup_slot = guitools.popup_menu(tbl, opt2_callback)
            tbl.customContextMenuRequested.connect(popup_slot)

        hheader = tbl.horizontalHeader()
        #set_header_context_menu(hheader)
        #set_table_context_menu(tbl)

        sort_col = hheader.sortIndicatorSection()
        sort_ord = hheader.sortIndicatorOrder()
        tbl.sortByColumn(0, QtCore.Qt.AscendingOrder)  # Basic Sorting
        tblWasBlocked = tbl.blockSignals(True)
        tbl.clear()
        tbl.setColumnCount(len(col_fancyheaders))
        tbl.setRowCount(len(row_list))
        tbl.verticalHeader().hide()
        tbl.setHorizontalHeaderLabels(col_fancyheaders)
        apply_table_column_widths(tblname, tbl, col_fancyheaders)
        tbl.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        tbl.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        tbl.setSortingEnabled(False)
        #dbg_col2_dtype = {}
        #def DEBUG_COL_DTYPE(col, dtype):
            #if not dtype in dbg_col2_dtype:
                #dbg_col2_dtype[dtype] = [col]
            #else:
                #if not col in dbg_col2_dtype[dtype]:
                    #dbg_col2_dtype[dtype].append(col)
        # Add items for each row and column
        for row in iter(row_list):
            data_tup = datatup_list[row]
            for col, data in enumerate(data_tup):
                item = QtWidgets.QTableWidgetItem()
                # BOOLEAN DATA
                if tools.is_bool(data):
                    check_state = QtCore.Qt.Checked if data else QtCore.Qt.Unchecked
                    item.setCheckState(check_state)
                    #DEBUG_COL_DTYPE(col, 'bool')
                    #item.setData(Qt.DisplayRole, bool(data))
                # INTEGER DATA
                elif tools.is_int(data):
                    item.setData(QtCore.Qt.DisplayRole, int(data))
                    #DEBUG_COL_DTYPE(col, 'int')
                # FLOAT DATA
                elif tools.is_float(data):
                    item.setData(QtCore.Qt.DisplayRole, float(data))
                    #DEBUG_COL_DTYPE(col, 'float')
                # STRING DATA
                else:
                    item.setText(str(data))
                    #DEBUG_COL_DTYPE(col, 'string')
                # Mark as editable or not
                if col_editable[col]:
                    item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
                    item.setBackground(QtGui.QColor(250, 240, 240))
                else:
                    item.setFlags(item.flags() ^ QtCore.Qt.ItemIsEditable)
                item.setTextAlignment(QtCore.Qt.AlignHCenter)
                tbl.setItem(row, col, item)

        #print(dbg_col2_dtype)
        tbl.setSortingEnabled(True)
        tbl.sortByColumn(sort_col, sort_ord)  # Move back to old sorting
        tbl.show()
        tbl.blockSignals(tblWasBlocked)

    def isItemEditable(self, item):
        return int(QtCore.Qt.ItemIsEditable & item.flags()) == int(QtCore.Qt.ItemIsEditable)

    #=======================
    # General Table Getters
    #=======================

    def get_tbl_header(front, tbl, col):
        # Map the fancy header back to the internal one.
        fancy_header = str(tbl.horizontalHeaderItem(col).text())
        return front.backend.resolve_table_header(fancy_header)

    def get_tbl_int(front, tbl, row, col):
        return int(tbl.item(row, col).text())

    def get_tbl_str(front, tbl, row, col):
        return str(tbl.item(row, col).text())

    def get_header_val(front, tbl, header, row):
        # RCOS TODO: This is hacky. These just need to be
        # in dicts to begin with.
        tblname = str(tbl.objectName()).replace('_TBL', '')
        tblname = tblname.replace('image', 'img')  # Sooooo hack
        # TODO: backmap from fancy headers to consise
        col = front.backend.get_table_column(tblname, header)
        return tbl.item(row, col).text()

    #=======================
    # Specific Item Getters
    #=======================

    def get_chiptbl_header(front, col):
        return front.get_tbl_header(front.ui.cxs_TBL, col)

    def get_imgtbl_header(front, col):
        return front.get_tbl_header(front.ui.gxs_TBL, col)

    def get_restbl_header(front, col):
        return front.get_tbl_header(front.ui.res_TBL, col)

    def get_nametbl_header(front, col):
        return front.get_tbl_header(front.ui.nxs_TBL, col)

    def get_restbl_cid(front, row):
        return int(front.get_header_val(front.ui.res_TBL, 'cid', row))

    def get_chiptbl_cid(front, row):
        return int(front.get_header_val(front.ui.cxs_TBL, 'cid', row))

    def get_nametbl_name(front, row):
        return str(front.get_header_val(front.ui.nxs_TBL, 'name', row))

    def get_nametbl_nx(front, row):
        return int(front.get_header_val(front.ui.nxs_TBL, 'nx', row))

    def get_imgtbl_gx(front, row):
        return int(front.get_header_val(front.ui.gxs_TBL, 'gx', row))

    #=======================
    # Table Changed Functions
    #=======================

    @slot_(QtWidgets.QTableWidgetItem)
    def img_tbl_changed(front, item):
        logger.debug("img_tbl_changed()")
        row, col = (item.row(), item.column())
        sel_gx = front.get_imgtbl_gx(row)
        header_lbl = front.get_imgtbl_header(col)
        new_val = item.checkState() == QtCore.Qt.Checked
        front.changeGxSignal.emit(sel_gx, header_lbl, new_val)

    @slot_(QtWidgets.QTableWidgetItem)
    def chip_tbl_changed(front, item):
        logger.debug("chip_tbl_changed()")
        row, col = (item.row(), item.column())
        sel_cid = front.get_chiptbl_cid(row)  # Get selected chipid
        new_val = csv_sanatize(item.text())   # sanatize for csv
        header_lbl = front.get_chiptbl_header(col)  # Get changed column
        front.changeCidSignal.emit(sel_cid, header_lbl, new_val)

    @slot_(QtWidgets.QTableWidgetItem)
    def res_tbl_changed(front, item):
        logger.debug("res_tbl_changed()")
        row, col = (item.row(), item.column())
        sel_cid  = front.get_restbl_cid(row)  # The changed row's chip id
        new_val  = csv_sanatize(item.text())  # sanatize val for csv
        header_lbl = front.get_restbl_header(col)  # Get changed column
        front.changeCidSignal.emit(sel_cid, header_lbl, new_val)

    @slot_(QtWidgets.QTableWidgetItem)
    def name_tbl_changed(front, item):
        logger.debug("name_tbl_changed()")
        row, col = (item.row(), item.column())
        sel_nx = front.get_nametbl_nx(row)    # The changed row's name index
        new_val  = csv_sanatize(item.text())  # sanatize val for csv
        header_lbl = front.get_nametbl_header(col)  # Get changed column
        front.aliasNameSignal.emit(sel_nx, header_lbl, new_val)

    #=======================
    # Table Clicked Functions
    #=======================
    @slot_(QtWidgets.QTableWidgetItem)
    @clicked
    def img_tbl_clicked(front, item):
        row = item.row()
        logger.debug("img_tbl_clicked(%r)", row)
        sel_gx = front.get_imgtbl_gx(row)
        front.selectGxSignal.emit(sel_gx)

    @slot_(QtWidgets.QTableWidgetItem)
    @clicked
    def chip_tbl_clicked(front, item):
        row, col = (item.row(), item.column())
        logger.debug("chip_tbl_clicked(%r, %r)", row, col)
        sel_cid = front.get_chiptbl_cid(row)
        front.selectCidSignal.emit(sel_cid)

    @slot_(QtWidgets.QTableWidgetItem)
    @clicked
    def res_tbl_clicked(front, item):
        row, col = (item.row(), item.column())
        logger.debug("res_tbl_clicked(%r, %r)", row, col)
        sel_cid = front.get_restbl_cid(row)
        front.selectResSignal.emit(sel_cid)

    @slot_(QtWidgets.QTableWidgetItem)
    @clicked
    def name_tbl_clicked(front, item):
        row, col = (item.row(), item.column())
        logger.debug("name_tbl_clicked(%r, %r)", row, col)
        sel_name = front.get_nametbl_name(row)
        front.selectNameSignal.emit(sel_name)

    #=======================
    # Other
    #=======================

    @slot_(int)
    def change_view(front, new_state):
        logger.debug("change_view(%r)", new_state)

    @slot_(str, str, list)
    def modal_useroption(front, msg, title, options):
        pass

    @slot_(str)
    def gui_write(front, msg_):
        app = QtWidgets.QApplication.instance()
        outputEdit = front.ui.outputEdit
        # Write msg to text area
        outputEdit.moveCursor(QtGui.QTextCursor.End)
        # TODO: Find out how to do backspaces in textEdit
        msg = str(msg_)
        if msg.find('\b') != -1:
            msg = msg.replace('\b', '') + '\n'
        outputEdit.insertPlainText(msg)
        if app is not None:
            app.processEvents()

    @slot_()
    def gui_flush(front):
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.processEvents()
        #front.ui.outputEdit.moveCursor(QtGui.QTextCursor.End)
        #front.ui.outputEdit.insertPlainText(msg)
