# HotSpotter port notes:
# Converted frontend signals/widgets to PyQt5 namespace imports.
# Centralized table display tweaks such as chip/name column widths.
# Moved menu action creation/wiring out of generated MainSkel.
# Loaded menu action source strings from hsgui.menu_strings for Qt translation.
# Replaced hscom.__common__ logging hooks with module-level logging.

import logging
import sys
# Qt
from PyQt5 import QtCore
from PyQt5 import QtGui
from PyQt5 import QtWidgets

# HotSpotter
from ._frontend.MainSkel import Ui_mainSkel
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
    back = front.back
    return {
        'menuFile': [
            action_spec('actionNew_Database', 'new_database', back.new_database, 'Ctrl+N'),
            action_spec('actionOpen_Database', 'open_database', back.open_database, 'Ctrl+O'),
            None,
            action_spec('actionSave_Database', 'save_database', back.save_database, 'Ctrl+S'),
            None,
            action_spec('actionImport_Img_file', 'import_img_file', back.import_images_from_file, 'Ctrl+I'),
            action_spec('actionImport_Img_dir', 'import_img_dir', back.import_images_from_dir),
            None,
            action_spec('actionQuit', 'quit', back.quit),
        ],
        'menuActions': [
            action_spec('actionAdd_Chip', 'add_chip', back.add_chip, 'A'),
            action_spec('actionNew_Chip_Property', 'new_chip_property', back.new_prop),
            None,
            action_spec('actionQuery', 'query', back.query, 'Q'),
            None,
            action_spec('actionReselect_ROI', 'reselect_roi', back.reselect_roi, 'R'),
            action_spec('actionReselect_Ori', 'reselect_ori', back.reselect_ori, 'O'),
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
            action_spec('actionLayout_Figures', 'layout_figures', back.layout_figures, 'Ctrl+L'),
            None,
            action_spec('actionPreferences', 'preferences', back.edit_preferences, 'Ctrl+P'),
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
            action_spec('actionDelete_computed_directory', 'delete_computed_directory', back.delete_cache),
            action_spec('actionDelete_global_preferences', 'delete_global_preferences', back.delete_global_prefs),
            None,
            action_spec('actionDev_Mode_IPython', 'dev_mode_ipython', back.dev_mode, 'Ctrl+Alt+Shift+D'),
            action_spec('actionDeveloper_Reload', 'developer_reload', back.dev_reload, 'Ctrl+Shift+R'),
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
        logger.debug(f"Connecting {name}")
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


#def popup(front, pos):
    #for i in front.ui.gxs_TBL.selectionModel().selection().indexes():
        #print(repr((i.row(), i.column())))
    #menu = QtWidgets.QMenu()
    #action1 = menu.addAction("action1")
    #action2 = menu.addAction("action2")
    #action3 = menu.addAction("action2")
    #action = menu.exec_(front.ui.gxs_TBL.mapToGlobal(pos))
    #print('action = %r ' % action)


def set_tabwidget_text(front, tblname, text):
    logger.debug(f"Set tab widget text {tblname}={text}")
    tablename2_tabwidget = {
        'gxs': front.ui.image_view,
        'cxs': front.ui.chip_view,
        'nxs': front.ui.name_view,
        'res': front.ui.result_view,
    }
    ui = front.ui
    tab_widget = tablename2_tabwidget[tblname]
    tab_index = ui.tablesTabWidget.indexOf(tab_widget)
    tab_text = _translate("mainSkel", text)
    ui.tablesTabWidget.setTabText(tab_index, tab_text)


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

    def __init__(front, back):
        super(MainWindowFrontend, front).__init__()
        front.prev_tbl_item = None
        front.ostream = None
        front.gui_logging_handler = None
        front.back = back
        front.ui = init_ui(front)
        create_menu_actions(front)
        # Progress bar is not hooked up yet
        front.ui.progressBar.setVisible(False)
        front.connect_signals()
        front.steal_stdout()

    def steal_stdout(front):
        return _steal_stdout(front)

    def return_stdout(front):
        return _return_stdout(front)


    @slot_()
    def closeEvent(front, event):
        event.accept()
        front.quitSignal.emit()

    def connect_signals(front):
        # Connect signals to slots
        back = front.back
        ui = front.ui
        # Frontend Signals
        front.printSignal.connect(back.backend_print)
        front.quitSignal.connect(back.quit)
        front.selectGxSignal.connect(back.select_gx)
        front.selectCidSignal.connect(back.select_cid)
        front.selectResSignal.connect(back.select_res_cid)
        front.selectNameSignal.connect(back.select_name)
        front.changeCidSignal.connect(back.change_chip_property)
        front.aliasNameSignal.connect(back.alias_name)
        front.changeGxSignal.connect(back.change_image_property)
        front.querySignal.connect(back.query)

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
        #front.printDBG('populate_tbl(%s)' % table_name)
        tblname = str(tblname)
        fancytab_dict = {
            'gxs': 'Image Table',
            'cxs': 'Chip Table',
            'nxs': 'Name Table',
            'res': 'Query Results Table',
        }
        tbl_dict = {
            'gxs': front.ui.gxs_TBL,
            'cxs': front.ui.cxs_TBL,
            'nxs': front.ui.nxs_TBL,
            'res': front.ui.res_TBL,
        }
        tbl = tbl_dict[tblname]
        #try:
            #tbl = front.ui.__dict__['%s_TBL' % tblname]
        #except KeyError:
            #ui_keys = front.ui.__dict__.keys()
            #tblname_list = [key for key in ui_keys if key.find('_TBL') >= 0]
            #msg = '\n'.join(['Invalid tblname = %s_TBL' % tblname,
                             #'valid names:\n  ' + '\n  '.join(tblname_list)])
            #raise Exception(msg)
        front._populate_table(tblname, tbl, col_fancyheaders, col_editable, row_list, datatup_list)
        # Set the tab text to show the number of items listed
        text = fancytab_dict[tblname] + ' : %d' % len(row_list)
        set_tabwidget_text(front, tblname, text)

    def _populate_table(front, tblname, tbl, col_fancyheaders, col_editable, row_list, datatup_list):
        # TODO: for chip table: delete metedata column
        # RCOS TODO:
        # I have a small right-click context menu working
        # Maybe one of you can put some useful functions in these?
        # RCOS TODO: How do we get the clicked item on a right click?
        # RCOS TODO:
        # The data tables should not use the item model
        # Instead they should use the more efficient and powerful
        # QAbstractItemModel / QAbstractTreeModel
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
                # RCOS TODO: Pass in datatype here.
                # BOOLEAN DATA
                if tools.is_bool(data) or data == 'True' or data == 'False':
                    check_state = QtCore.Qt.Checked if bool(data) else QtCore.Qt.Unchecked
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
        header = (front.back.reverse_fancy[fancy_header]
                  if fancy_header in front.back.reverse_fancy else fancy_header)
        return header

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
        col = front.back.table_headers[tblname].index(header)
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
        logger.debug(f"img_tbl_clicked({row!r})")
        sel_gx = front.get_imgtbl_gx(row)
        front.selectGxSignal.emit(sel_gx)

    @slot_(QtWidgets.QTableWidgetItem)
    @clicked
    def chip_tbl_clicked(front, item):
        row, col = (item.row(), item.column())
        logger.debug(f"chip_tbl_clicked({row!r}, {col!r})")
        sel_cid = front.get_chiptbl_cid(row)
        front.selectCidSignal.emit(sel_cid)

    @slot_(QtWidgets.QTableWidgetItem)
    @clicked
    def res_tbl_clicked(front, item):
        row, col = (item.row(), item.column())
        logger.debug(f"res_tbl_clicked({row!r}, {col!r})")
        sel_cid = front.get_restbl_cid(row)
        front.selectResSignal.emit(sel_cid)

    @slot_(QtWidgets.QTableWidgetItem)
    @clicked
    def name_tbl_clicked(front, item):
        row, col = (item.row(), item.column())
        logger.debug(f"name_tbl_clicked({row!r}, {col!r})")
        sel_name = front.get_nametbl_name(row)
        front.selectNameSignal.emit(sel_name)

    #=======================
    # Other
    #=======================

    @slot_(int)
    def change_view(front, new_state):
        tab_name = str(front.ui.tablesTabWidget.tabText(new_state))
        logger.debug(f"change_view({new_state!r})")
        prevBlock = front.ui.tablesTabWidget.blockSignals(True)
        front.ui.tablesTabWidget.blockSignals(prevBlock)
        if tab_name.startswith('Query Results Table'):
            logger.debug(f"Current cache uid: {front.back.hs.get_cache_uid()}")

    @slot_(str, str, list)
    def modal_useroption(front, msg, title, options):
        pass

    @slot_(str)
    def gui_write(front, msg_):
        app = front.back.app
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
        app = front.back.app
        if app is not None:
            app.processEvents()
        #front.ui.outputEdit.moveCursor(QtGui.QTextCursor.End)
        #front.ui.outputEdit.insertPlainText(msg)
