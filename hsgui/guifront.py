# HotSpotter port notes:
# Converted frontend signals/widgets to PyQt5 namespace imports.
# Centralized table display tweaks such as chip/name column widths.
# Moved menu action creation/wiring out of generated MainSkel.
# Loaded menu action source strings from hsgui.menu_strings for Qt translation.
# Replaced hscom.__common__ logging hooks with module-level logging.

import functools
import logging
from os.path import exists, join
import sys
# Qt
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

# HotSpotter
from ._frontend.ChipPropertyDialog import ChipPropertyDialog
from ._frontend.CleanNameTableDialog import CleanNameTableDialog
from ._frontend.DeleteChipPropertyDialog import DeleteChipPropertyDialog
from ._frontend.MainSkel import Ui_mainSkel
from ._frontend.TableFilterDialog import TableFilterDialog
from . import guitools
from . import menu_strings
from .guitablemodel import DataTableModel
from .guitablemodel import DataTableProxyModel
from .guitools import slot_
from .guitools import blocking
from hotspotter import chip_properties

logger = logging.getLogger(__name__)


def translate(context, text):
    """Translate user-facing text while preserving an absent value."""
    if text is None:
        return None
    return QtWidgets.QApplication.translate(context, text)

#=================
# Globals
#=================

IS_INIT = False
NOSTEAL_OVERRIDE = False  # Hard disable switch for stream stealer

TABLE_COLUMN_WIDTH_FACTORS = {
    'cxs': {'name': 2.0},
    'nxs': {'name': 2.0},
}

TABLE_TAB_LABELS = {
    'gxs': 'Image Table',
    'cxs': 'Chip Table',
    'nxs': 'Name Table',
    'res': 'Query Results Table',
}

TABLE_HEADER_LABELS = {
    'gx':         'Image Index',
    'nx':         'Name Index',
    'cid':        'Chip ID',
    'aif':        'All Detected',
    'gname':      'Image Name',
    'nCxs':       '#Chips',
    'name':       'Name',
    'nGt':        '#GT',
    'nKpts':      '#Kpts',
    'theta':      'Theta',
    'roi':        'ROI (x, y, w, h)',
    'rank':       'Rank',
    'score':      'Confidence',
    'match_name': 'Matching Name',
}


#=================
# Helpers
#=================

try:
    _fromUtf8 = QtCore.QString.fromUtf8
except AttributeError:
    _fromUtf8 = lambda s: s

def csv_sanatize(str_):
    return str(str_).replace(',', ';;')


def _selected_chip_confirmation_context(front, *args, **kwargs):
    """Capture a stable chip ID before opening a modal confirmation."""
    cid = kwargs.get('cid')
    if cid is None:
        context = front.backend.get_selected_chip_context()
        if context is None:
            return None
        cid = context['cid']
    return {'cid': int(cid)}


def _selected_image_confirmation_context(front, *args, **kwargs):
    """Capture a stable image index before opening a modal confirmation."""
    gx = kwargs.get('gx')
    if gx is None:
        gx = front.backend.get_selected_gx()
    return None if gx is None else {'gx': int(gx)}


def confirm_action(confirmation_key, context_provider=None,
                   confirmation_callback=None):
    """Decorate an action with a translated confirmation and optional context.

    A context provider returns keyword values used both to format the message
    and to invoke the wrapped action. Returning ``None`` bypasses confirmation
    so the action can preserve its existing missing-context handling. A custom
    confirmation callback may replace the standard Yes/No dialog.
    """
    def decorator(action):
        @functools.wraps(action)
        def confirmed_action(front, *args, **kwargs):
            context = {}
            if context_provider is not None:
                context = context_provider(front, *args, **kwargs)
                if context is None:
                    return action(front, *args, **kwargs)
            call_kwargs = dict(kwargs)
            call_kwargs.update(context)
            title = translate(
                menu_strings.MENU_CONTEXT,
                menu_strings.confirmation_title(confirmation_key),
            )
            message = translate(
                menu_strings.MENU_CONTEXT,
                menu_strings.confirmation_message(confirmation_key),
            )
            if context:
                message = message % context
            callback = confirmation_callback or guitools.confirm_action
            if not callback(front, title, message):
                logger.info(
                    "Cancelled action requiring confirmation: %s",
                    confirmation_key,
                )
                return False
            return action(front, *args, **call_kwargs)
        return confirmed_action
    return decorator


def display_table_header(header):
    """Return the user-facing label for an internal table column key."""
    return TABLE_HEADER_LABELS.get(header, header)


def apply_table_column_widths(tblname, tbl, col_headers):
    """Apply per-table display width preferences after headers are created."""
    width_factors = TABLE_COLUMN_WIDTH_FACTORS.get(tblname, {})
    if not width_factors:
        return
    default_width = tbl.horizontalHeader().defaultSectionSize()
    for header, factor in width_factors.items():
        if header in col_headers:
            col = col_headers.index(header)
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
    # The GUI pane is user-facing. Detailed diagnostics remain available in
    # the configured debug log without flooding normal interactive sessions.
    handler.setLevel(logging.INFO)
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
            action_spec('actionClear_Filter', 'clear_filter', front.clear_table_filters, 'Ctrl+Shift+F'),
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
            action_spec('actionPrevious', 'previous', back.select_previous, 'B'),
            action_spec('actionNext', 'next', back.select_next, 'N'),
            action_spec('actionPrevious_Unannotated', 'previous_unannotated', back.select_previous_unannotated, 'Shift+B'),
            action_spec('actionNext_Unannotated', 'next_unannotated', back.select_next_unannotated, 'Shift+N'),
            None,
            action_spec('actionDelete_Chip', 'delete_chip', front.delete_chip, 'Ctrl+Del'),
            action_spec('actionDelete_Image', 'delete_image', front.delete_image, 'Ctrl+Shift+Del'),
            action_spec('actionClean_Name_Table', 'clean_name_table', front.clean_name_table),
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
            action_spec('actionDelete_Precomputed_Results', 'delete_precomputed_results', front.delete_queryresults_dir),
            action_spec('actionDelete_computed_directory', 'delete_computed_directory', front.delete_cache),
            action_spec('actionDelete_global_preferences', 'delete_global_preferences', front.delete_global_prefs),
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
                            text=translate(
                                menu_strings.MENU_CONTEXT,
                                menu_strings.text(i18n_key),
                            ),
                            shortcut=spec.get('shortcut'),
                            tooltip=translate(
                                menu_strings.MENU_CONTEXT,
                                menu_strings.tooltip(i18n_key),
                            ),
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
    selectNxSignal = QtCore.pyqtSignal(int)
    changeCidSignal = QtCore.pyqtSignal(int, str, str)
    aliasNameSignal = QtCore.pyqtSignal(int, str, str)
    changeGxSignal  = QtCore.pyqtSignal(int, str, bool)
    querySignal = QtCore.pyqtSignal()

    def __init__(front, backend, parent=None):
        super(MainWindowFrontend, front).__init__(parent)
        front.prev_table_click = None
        front.ostream = None
        front.gui_logging_handler = None
        front.backend = backend
        # temp import for debug  purposes
        # from .guiback import MainWindowBackend
        # front.backend: MainWindowBackend = backend
        front._backend_block_stack = []
        front.edit_prefs = None
        front.ui = init_ui(front)
        front._init_table_models()
        create_menu_actions(front)
        # Progress bar is not hooked up yet
        front.ui.progressBar.setVisible(False)
        front.connect_signals()
        front.steal_stdout()
        from hsviz import draw_func2 as df2
        df2.register_qt_win(front)

    def _init_table_models(front):
        """Attach one persistent source model and proxy to each table view."""
        front.table_views = {
            'gxs': front.ui.gxs_TBL,
            'cxs': front.ui.cxs_TBL,
            'nxs': front.ui.nxs_TBL,
            'res': front.ui.res_TBL,
        }
        front.table_models = {}
        front.table_proxies = {}
        front.table_sort_state = {
            'gxs': (0, QtCore.Qt.AscendingOrder),
            'cxs': (0, QtCore.Qt.AscendingOrder),
            'nxs': (0, QtCore.Qt.DescendingOrder),
            'res': (0, QtCore.Qt.AscendingOrder),
        }
        front.table_initialized = {
            tblname: False for tblname in front.table_views
        }
        for tblname, view in front.table_views.items():
            model = DataTableModel(parent=front)
            proxy = DataTableProxyModel(parent=front)
            proxy.setSourceModel(model)
            view.setModel(proxy)
            view.verticalHeader().hide()
            view.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
            view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            view.setSortingEnabled(True)
            model.cell_edited.connect(
                lambda record_id, column_key, value, table=tblname:
                front.table_cell_edited(table, record_id, column_key, value)
            )
            front.table_models[tblname] = model
            front.table_proxies[tblname] = proxy

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

    #========================
    # menu files
    #========================

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
    def quit_application(front):
        guitools.exit_application()

    #========================
    # view menu
    #========================

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
    def filter_table(front):
        tblname, _ = front.current_table()
        model = front.table_models[tblname]
        proxy = front.table_proxies[tblname]
        columns = [
            (definition['key'], definition['header'])
            for definition in model.column_definitions()
        ]
        if not columns:
            logger.warning(
                "[filter] There is no columns to filter in table %s.",
                tblname,
            )
            QtWidgets.QMessageBox.information(
                front,
                translate('TableFilterDialog', 'Filter Table'),
                translate(
                    'TableFilterDialog',
                    'The current table has no columns to filter.',
                ),
            )
            return

        conditions = proxy.filters()
        while True:
            dialog = TableFilterDialog(columns, conditions, front)
            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                return
            conditions = dialog.conditions()
            try:
                proxy.set_filters(conditions)
            except ValueError as ex:
                QtWidgets.QMessageBox.warning(
                    front,
                    translate('TableFilterDialog', 'Invalid Table Filter'),
                    str(ex),
                )
                continue
            front.prev_table_click = None
            front.update_table_tab_count(tblname)
            return

    @slot_()
    def clear_table_filters(front):
        """Clear all frontend proxy filters and refresh visible table rows."""
        for tblname, proxy in front.table_proxies.items():
            proxy.clear_filters()
            front.table_views[tblname].viewport().update()
            front.update_table_tab_count(tblname)
        front.prev_table_click = None
        logger.info("Cleared filters from all tables")

    #========================
    # actions menu
    #========================

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
    def new_prop(front):
        definition = None
        while True:
            dialog = ChipPropertyDialog(definition, front)
            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                return
            definition = dialog.definition()
            try:
                front.backend.new_prop(definition)
            except (KeyError, TypeError, ValueError) as ex:
                QtWidgets.QMessageBox.warning(
                    front,
                    'Invalid Chip Property',
                    str(ex),
                )
                continue
            return

    @slot_()
    @blocking
    def reselect_roi(front):
        context = front.backend.get_selected_chip_context()
        if context is None:
            front.show_information(
                'Reselect ROI', 'Cannot reselect ROI. No chip selected')
            return
        edit_applied = False
        front.backend.close_chip_figure()
        try:
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
                edit_applied = True
        finally:
            if not edit_applied:
                front.backend.show_chip(context['cx'])

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
        edit_applied = False
        front.backend.close_chip_figure()
        try:
            front.backend.show_image(
                context['gx'],
                [context['cx']],
                figtitle='Image View - Select Orientation (click two points)',
            )
            theta = guitools.select_orientation()
            if theta is not None:
                front.backend.reselect_ori(theta=theta)
                edit_applied = True
        finally:
            if not edit_applied:
                front.backend.show_chip(context['cx'])

    @slot_()
    @blocking
    @confirm_action(
        'delete_chip',
        context_provider=_selected_chip_confirmation_context,
    )
    def delete_chip(front, cid=None):
        if cid is None:
            front.backend.delete_chip()
            return False
        front.backend.delete_chip(cid=cid)
        return True

    @slot_()
    @blocking
    @confirm_action(
        'delete_image',
        context_provider=_selected_image_confirmation_context,
    )
    def delete_image(front, gx=None):
        if gx is None:
            front.backend.delete_image()
            return False
        front.backend.delete_image(gx=gx)
        return True

    @slot_()
    def clean_name_table(front):
        unused_name_rows = front.backend.get_unused_name_rows()
        if not unused_name_rows:
            front.show_information(
                translate('CleanNameTableDialog', 'Clean Name Table'),
                translate(
                    'CleanNameTableDialog',
                    'The name table has no zero-chip names to remove.',
                ),
            )
            return
        dialog = CleanNameTableDialog(unused_name_rows, front)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            front.backend.clean_name_table()

    #========================
    # options menu
    #========================

    @slot_()
    def edit_preferences(front):
        preferences = front.backend.get_preferences()
        front.edit_prefs = front.show_preferences(
            preferences,
            front.backend.default_preferences,
        )
        query_uid = ''.join(preferences.query_cfg.get_uid())
        logger.debug("query_uid = %s", query_uid)

    #========================
    # help menu
    #========================

    @slot_()
    @confirm_action('delete_precomputed_results')
    def delete_queryresults_dir(front):
        front.backend.delete_queryresults_dir()
        return True

    @slot_()
    @confirm_action('delete_computed_directory')
    def delete_cache(front):
        front.backend.delete_cache()
        return True

    @slot_()
    @confirm_action('delete_global_preferences')
    def delete_global_prefs(front):
        front.backend.delete_global_prefs()
        return True

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

    #========================
    # dialog helpers
    #========================

    def show_preferences(front, preferences, default_callback):
        widget = preferences.createQWidget()
        widget.ui.defaultPrefsBUT.clicked.connect(default_callback)
        return widget

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
        front.selectNxSignal.connect(back.select_nx)
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
        back.layoutFiguresSignal.connect(front.layout_figures)
        back.chipCellUpdateSignal.connect(front.update_chip_table_cell)

        # Gui Components
        # Table views
        ui.cxs_TBL.clicked.connect(front.chip_tbl_clicked)
        ui.gxs_TBL.clicked.connect(front.img_tbl_clicked)
        ui.res_TBL.clicked.connect(front.res_tbl_clicked)
        ui.nxs_TBL.clicked.connect(front.name_tbl_clicked)
        chip_header = ui.cxs_TBL.horizontalHeader()
        chip_header.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        chip_header.customContextMenuRequested.connect(
            front.chip_header_context_requested
        )
        ui.cxs_TBL.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        ui.cxs_TBL.customContextMenuRequested.connect(
            front.chip_cell_context_requested
        )
        # Tab Widget
        ui.tablesTabWidget.currentChanged.connect(front.change_view)

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
    def populate_tbl(front, tblname, col_headers, col_editable,
                     record_ids, datatup_list):
        tblname = str(tblname)
        view = front.table_views[tblname]
        model = front.table_models[tblname]
        proxy = front.table_proxies[tblname]
        selected_ids = front.selected_record_ids(tblname)
        header = view.horizontalHeader()
        sort_column, sort_order = front.table_sort_state[tblname]
        if front.table_initialized[tblname]:
            sort_column = header.sortIndicatorSection()
            sort_order = header.sortIndicatorOrder()
        if sort_column < 0 or sort_column >= len(col_headers):
            sort_column = 0
        front.table_sort_state[tblname] = (sort_column, sort_order)

        if len(record_ids) != len(datatup_list):
            raise ValueError(
                '%s table has %d record IDs for %d rows' % (
                    tblname, len(record_ids), len(datatup_list)
                )
            )
        columns = front.table_column_definitions(
            tblname,
            col_headers,
            col_editable,
        )
        rows = list(zip(record_ids, datatup_list))
        model.set_table(columns, rows)
        proxy.pin_first_row = tblname == 'res' and bool(rows)
        proxy.set_filters(proxy.filters())
        if columns:
            proxy.sort(sort_column, sort_order)
            view.sortByColumn(sort_column, sort_order)
        apply_table_column_widths(tblname, view, col_headers)
        front.restore_table_selection(tblname, selected_ids)
        front.prev_table_click = None
        front.table_initialized[tblname] = True
        view.show()
        front.update_table_tab_count(tblname)

    def table_column_definitions(front, tblname, col_headers, col_editable):
        columns = []
        for column_key, editable in zip(col_headers, col_editable):
            property_definition = None
            if tblname == 'cxs':
                property_definition = (
                    front.backend.get_chip_property_definition(column_key)
                )
            checkable = column_key == 'aif' or (
                property_definition is not None
                and property_definition.get('datatype') == 'bool'
            )
            nullable = (
                property_definition is not None
                and property_definition.get('datatype') == 'bool'
            )
            columns.append({
                'key': column_key,
                'header': display_table_header(column_key),
                'editable': bool(editable),
                'checkable': checkable,
                'nullable': nullable,
                'alignment': int(
                    QtCore.Qt.AlignHCenter | QtCore.Qt.AlignVCenter
                ),
            })
        return columns

    def update_table_tab_count(front, tblname):
        table_tabs = {
            'gxs': front.ui.image_view,
            'cxs': front.ui.chip_view,
            'nxs': front.ui.name_view,
            'res': front.ui.result_view,
        }
        ui = front.ui
        tab_widget = table_tabs[tblname]
        tab_index = ui.tablesTabWidget.indexOf(tab_widget)
        tab_text = translate(
            "mainSkel",
            "%s (%d)" % (
                TABLE_TAB_LABELS[tblname],
                front.table_proxies[tblname].rowCount(),
            ),
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

    #=======================
    # General Table Access
    #=======================

    def table_column_key(front, tbl, col):
        """Return an internal column key for a table view column."""
        tblname = front.table_name_for_view(tbl)
        return front.table_models[tblname].column_key(col)

    def table_name_for_view(front, view):
        for tblname, candidate in front.table_views.items():
            if candidate is view:
                return tblname
        raise KeyError('Unknown table view')

    def table_source_index(front, tblname, proxy_index):
        if not proxy_index.isValid():
            return QtCore.QModelIndex()
        return front.table_proxies[tblname].mapToSource(proxy_index)

    def selected_record_ids(front, tblname):
        view = front.table_views[tblname]
        selection_model = view.selectionModel()
        if selection_model is None:
            return []
        proxy_indexes = selection_model.selectedRows()
        if not proxy_indexes:
            seen_rows = set()
            proxy_indexes = []
            for index in selection_model.selectedIndexes():
                if index.row() not in seen_rows:
                    seen_rows.add(index.row())
                    proxy_indexes.append(index)
        model = front.table_models[tblname]
        record_ids = []
        seen_ids = set()
        for proxy_index in proxy_indexes:
            source_index = front.table_source_index(tblname, proxy_index)
            if source_index.isValid():
                record_id = model.record_id_at(source_index.row())
                if record_id not in seen_ids:
                    seen_ids.add(record_id)
                    record_ids.append(record_id)
        return record_ids

    def restore_table_selection(front, tblname, record_ids):
        if not record_ids:
            return
        view = front.table_views[tblname]
        model = front.table_models[tblname]
        proxy = front.table_proxies[tblname]
        selection_model = view.selectionModel()
        first = True
        for record_id in record_ids:
            source_row = model.source_row_for_id(record_id)
            if source_row is None or model.columnCount() == 0:
                continue
            source_index = model.index(source_row, 0)
            proxy_index = proxy.mapFromSource(source_index)
            if not proxy_index.isValid():
                continue
            flags = QtCore.QItemSelectionModel.Rows
            flags |= (
                QtCore.QItemSelectionModel.ClearAndSelect
                if first else QtCore.QItemSelectionModel.Select
            )
            if first:
                selection_model.setCurrentIndex(proxy_index, flags)
            else:
                selection_model.select(proxy_index, flags)
            first = False

    def table_click_record_id(front, tblname, proxy_index):
        source_index = front.table_source_index(tblname, proxy_index)
        if not source_index.isValid():
            return None
        model = front.table_models[tblname]
        if model.flags(source_index) & QtCore.Qt.ItemIsEditable:
            logger.debug("Ignoring click on editable column")
            return None
        record_id = model.record_id_at(source_index.row())
        click = (tblname, record_id, model.column_key(source_index.column()))
        if click == front.prev_table_click:
            return None
        front.prev_table_click = click
        return record_id

    @slot_(QtCore.QPoint)
    def chip_header_context_requested(front, pos):
        """Open property actions for a user-defined chip-table column."""
        header = front.ui.cxs_TBL.horizontalHeader()
        col = header.logicalIndexAt(pos)
        if col < 0:
            return
        column_key = front.table_column_key(front.ui.cxs_TBL, col)
        definition = front.backend.get_chip_property_definition(column_key)
        if definition is None:
            return
        menu = QtWidgets.QMenu(front)
        edit_action = menu.addAction('Edit Property...')
        delete_action = menu.addAction('Delete Property...')
        selected = menu.exec_(header.mapToGlobal(pos))
        if selected is edit_action:
            front.edit_chip_property(column_key, definition)
        elif selected is delete_action:
            front.confirm_delete_chip_property(column_key)

    @slot_(QtCore.QPoint)
    def chip_cell_context_requested(front, pos):
        """Open value actions for a user-defined chip metadata cell."""
        view = front.ui.cxs_TBL
        proxy_index = view.indexAt(pos)
        if not proxy_index.isValid():
            return
        source_index = front.table_source_index('cxs', proxy_index)
        if not source_index.isValid():
            return
        model = front.table_models['cxs']
        column_key = model.column_key(source_index.column())
        definition = front.backend.get_chip_property_definition(column_key)
        if (
            definition is None
            or not (model.flags(source_index) & QtCore.Qt.ItemIsEditable)
        ):
            return

        menu = QtWidgets.QMenu(front)
        edit_action = menu.addAction('Edit')
        delete_action = menu.addAction('Delete Content')
        selected = menu.exec_(view.viewport().mapToGlobal(pos))
        if selected is edit_action:
            front.edit_chip_table_cell(proxy_index)
        elif selected is delete_action:
            front.clear_chip_table_cell(proxy_index)

    def edit_chip_table_cell(front, proxy_index):
        """Start the table's normal editor for a chip metadata cell."""
        view = front.ui.cxs_TBL
        source_index = front.table_source_index('cxs', proxy_index)
        if not source_index.isValid():
            return False
        model = front.table_models['cxs']
        column_key = model.column_key(source_index.column())
        if (
            front.backend.get_chip_property_definition(column_key) is None
            or not (model.flags(source_index) & QtCore.Qt.ItemIsEditable)
        ):
            return False
        view.setCurrentIndex(proxy_index)
        view.edit(proxy_index)
        return True

    def clear_chip_table_cell(front, proxy_index):
        """Reset one user-defined chip metadata value to empty."""
        source_index = front.table_source_index('cxs', proxy_index)
        if not source_index.isValid():
            return False
        model = front.table_models['cxs']
        column_key = model.column_key(source_index.column())
        if (
            front.backend.get_chip_property_definition(column_key) is None
            or not (model.flags(source_index) & QtCore.Qt.ItemIsEditable)
        ):
            return False
        return model.setData(source_index, '', QtCore.Qt.EditRole)

    def edit_chip_property(front, column_key, definition=None):
        definition = (
            definition
            or front.backend.get_chip_property_definition(column_key)
        )
        while definition is not None:
            dialog = ChipPropertyDialog(definition, front)
            if dialog.exec_() != QtWidgets.QDialog.Accepted:
                return
            updated_definition = dialog.definition()
            conditions = front.table_proxies['cxs'].filters()
            try:
                new_key = front.backend.update_chip_property_definition(
                    column_key,
                    updated_definition,
                )
            except (KeyError, TypeError, ValueError) as ex:
                QtWidgets.QMessageBox.warning(
                    front,
                    'Invalid Chip Property',
                    str(ex),
                )
                definition = updated_definition
                continue
            if column_key in conditions:
                conditions[new_key] = conditions.pop(column_key)
                front.table_proxies['cxs'].set_filters(conditions)
                front.update_table_tab_count('cxs')
            return

    def confirm_delete_chip_property(front, column_key):
        dialog = DeleteChipPropertyDialog(column_key, front)
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            front.backend.delete_chip_property(column_key)
            front.table_proxies['cxs'].remove_filter_key(column_key)
            front.update_table_tab_count('cxs')

    #=======================
    # Table Changed Functions
    #=======================

    def table_cell_edited(front, tblname, record_id, column_key, value):
        """Dispatch a model edit to the backend using its stable record ID."""
        logger.debug(
            "Table edit table=%r record_id=%r column=%r",
            tblname,
            record_id,
            column_key,
        )
        if tblname == 'gxs':
            front.changeGxSignal.emit(
                int(record_id), str(column_key), bool(value)
            )
            return
        if tblname in ('cxs', 'res'):
            definition = front.backend.get_chip_property_definition(column_key)
            if definition is not None and definition['datatype'] == 'bool':
                if chip_properties.is_empty_property_value(value):
                    new_value = ''
                else:
                    new_value = 'true' if bool(value) else 'false'
            else:
                new_value = csv_sanatize(value)
            front.changeCidSignal.emit(
                int(record_id), str(column_key), new_value
            )
            return
        if tblname == 'nxs':
            front.aliasNameSignal.emit(
                int(record_id), str(column_key), csv_sanatize(value)
            )
            return
        raise KeyError('Unknown table %r' % (tblname,))

    @slot_(int, str, object)
    def update_chip_table_cell(front, cid, column_key, value):
        """Apply a backend-normalized chip value without rebuilding a table."""
        updated = front.table_models['cxs'].update_value(
            cid,
            str(column_key),
            value,
        )
        if not updated:
            logger.warning(
                "Could not refresh missing chip cell cid=%r key=%r",
                cid,
                column_key,
            )

    #=======================
    # Table Clicked Functions
    #=======================
    @slot_(QtCore.QModelIndex)
    def img_tbl_clicked(front, proxy_index):
        logger.debug("img_tbl_clicked(%r)", proxy_index.row())
        record_id = front.table_click_record_id('gxs', proxy_index)
        if record_id is not None:
            front.selectGxSignal.emit(int(record_id))

    @slot_(QtCore.QModelIndex)
    def chip_tbl_clicked(front, proxy_index):
        logger.debug(
            "chip_tbl_clicked(%r, %r)",
            proxy_index.row(),
            proxy_index.column(),
        )
        record_id = front.table_click_record_id('cxs', proxy_index)
        if record_id is not None:
            front.selectCidSignal.emit(int(record_id))

    @slot_(QtCore.QModelIndex)
    def res_tbl_clicked(front, proxy_index):
        logger.debug(
            "res_tbl_clicked(%r, %r)",
            proxy_index.row(),
            proxy_index.column(),
        )
        record_id = front.table_click_record_id('res', proxy_index)
        if record_id is not None:
            front.selectResSignal.emit(int(record_id))

    @slot_(QtCore.QModelIndex)
    def name_tbl_clicked(front, proxy_index):
        logger.debug(
            "name_tbl_clicked(%r, %r)",
            proxy_index.row(),
            proxy_index.column(),
        )
        record_id = front.table_click_record_id('nxs', proxy_index)
        if record_id is not None:
            front.selectNxSignal.emit(int(record_id))

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
