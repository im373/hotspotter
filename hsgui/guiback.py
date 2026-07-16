# HotSpotter port notes:
# Updated backend GUI workflows for PyQt5 signal/slot behavior.
# Kept image/chip/query actions compatible with Python 3 data types.
# Split image-only Select Next from Select Next Unannotated behavior.
# Reused backend selection helpers and HotSpotterAPI chip counts for navigation.
# Replaced hscom.__common__ logging/profile hooks with logging and hscom.profiling.


# Python
import fnmatch
import logging
from os.path import split, join
import re
import sys
# Qt
from PyQt5 import QtCore
# Science
import numpy as np
# Hotspotter
from .guitools import drawing, slot_
from .guitools import backblocking as blocking
from hscom import helpers as util
from hscom import fileio as io
from hscom.logging_utils import DEPRECATED
from hscom import params
from hscom.profiling import profile
from hsviz import draw_func2 as df2
from hsviz import viz
from hsviz import interact
from hotspotter import HotSpotterAPI

logger = logging.getLogger(__name__)

FNUMS = dict(image=1, chip=2, res=3, inspect=4, special=5, name=6)
viz.register_FNUMS(FNUMS)


# Table Filter

def normalize_table_filter(condition):
    """Return ``None`` for an inactive filter and stripped text otherwise."""
    if condition is None:
        return None
    condition = str(condition).strip()
    if not condition or condition.lower() == 'none':
        return None
    return condition


def compile_table_filters(headers, conditions):
    """Compile column conditions into ``(column, predicate)`` pairs."""
    compiled = []
    for header, condition in conditions.items():
        condition = normalize_table_filter(condition)
        if condition is None or header not in headers:
            continue
        column = headers.index(header)
        if condition.startswith('re:'):
            pattern = condition[3:]
            try:
                regex = re.compile(pattern)
            except re.error as ex:
                raise ValueError(
                    "Invalid regular expression for %s: %s" % (header, ex)
                )
            predicate = lambda value, regex=regex: (
                regex.fullmatch(str(value)) is not None
            )
        elif any(char in condition for char in '*?['):
            predicate = lambda value, pattern=condition: fnmatch.fnmatchcase(
                str(value), pattern
            )
        else:
            predicate = lambda value, expected=condition: str(value) == expected
        compiled.append((column, predicate))
    return compiled


def filter_table_rows(headers, rows, conditions):
    """Return rows satisfying every active column condition."""
    compiled = compile_table_filters(headers, conditions)
    if not compiled:
        return list(rows)
    return [
        row
        for row in rows
        if all(column < len(row) and predicate(row[column])
               for column, predicate in compiled)
    ]


def make_table_header_lists(table_headers, editable_headers, property_keys=None):
    """Build backend column names and editability flags for a table payload."""
    property_keys = [] if property_keys is None else property_keys
    column_headers = table_headers[:] + property_keys
    column_editable = [False] * len(table_headers) + [True] * len(property_keys)
    for header in editable_headers:
        column_editable[column_headers.index(header)] = True
    return column_headers, column_editable


# Image Selection

def _close_chip_figure_if_open():
    fnum = FNUMS['chip']
    if df2.plt.fignum_exists(fnum):
        fig = df2.plt.figure(fnum)
        df2.close_figure(fig)


def select_next_image(back, next_unannotated=False):
    current_gx = back.get_selected_gx()
    current_gx = -1 if current_gx is None else int(current_gx)
    for gx in iter(back.hs.get_valid_gxs()):
        gx = int(gx)
        is_next = gx > current_gx
        is_unannotated = back.hs.gx2_nChips(gx) == 0
        if is_next and (not next_unannotated or is_unannotated):
            _close_chip_figure_if_open()
            back.select_gx(gx, show_chip_splash=False)
            return None
    if next_unannotated:
        return 'All following images already have chips.'
    return 'end of the image list'


def _strict_mode():
    args = getattr(params, 'args', None)
    return getattr(args, 'strict', False) or '--strict' in sys.argv


def _report_backend_exception(back, title, message, ex):
    logger.exception("%s: %s", title, message)
    detail = '%s\n\n%s: %s' % (message, type(ex).__name__, ex)
    back.operationFailedSignal.emit(title, detail)
    if _strict_mode():
        raise


#------------------------
# Backend MainWindow Class
#------------------------
class MainWindowBackend(QtCore.QObject):
    """Own application operations and emit presentation update signals."""
    # Backend Signals
    populateSignal = QtCore.pyqtSignal(str, list, list, list, list)
    setEnabledSignal = QtCore.pyqtSignal(bool)
    windowTitleSignal = QtCore.pyqtSignal(str)
    busySignal = QtCore.pyqtSignal(bool)
    informationSignal = QtCore.pyqtSignal(str, str)
    operationFailedSignal = QtCore.pyqtSignal(str, str)
    apiConnectedSignal = QtCore.pyqtSignal()

    #------------------------
    # Constructor
    #------------------------
    def __init__(back, hs=None, parent=None):
        super(MainWindowBackend, back).__init__(parent)
        back.current_res = None
        back.selection = None
        back.table_filters = {}

        # A map from short internal headers to fancy headers seen by the user
        back.fancy_headers = {
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
        back.reverse_fancy = {v: k for (k, v) in list(back.fancy_headers.items())}

        # A list of default internal headers to display
        back.table_headers = {
            'gxs':  ['gx', 'gname', 'nCxs', 'aif'],
            'cxs':  ['cid', 'name', 'gname', 'nGt', 'nKpts', 'theta'],
            'nxs':  ['nx', 'name', 'nCxs'],
            'res':  ['rank', 'score', 'name', 'cid']
        }

        # Lists internal headers whos items are editable
        back.table_editable = {
            'gxs':  [],
            'cxs':  ['name'],
            'nxs':  ['name'],
            'res':  ['name'],
        }

        back.hs = hs

    #------------------------
    # Draw Functions
    #------------------------

    @drawing
    @profile
    def show_splash(back, fnum, view='Nice', **kwargs):
        if df2.plt.fignum_exists(fnum):
            df2.figure(fnum=fnum, docla=True, doclf=True)
            viz.show_splash(fnum=fnum)
            df2.set_figtitle('%s View' % view)

    def _layout_figures_if(back, did_exist):
        #back._layout_figures_if(did_exist)
        pass

    @drawing
    @profile
    def show_image(back, gx, sel_cxs=[], figtitle='Image View', **kwargs):
        fnum = FNUMS['image']
        did_exist = df2.plt.fignum_exists(fnum)
        kwargs.pop('nodraw', None)
        df2.figure(fnum=fnum, docla=True, doclf=True)
        interact.interact_image(back.hs, gx, sel_cxs, back.select_cx,
                                fnum=fnum, figtitle=figtitle, nodraw=True,
                                **kwargs)
        back._layout_figures_if(did_exist)

    @drawing
    @profile
    def show_chip(back, cx, **kwargs):
        fnum = FNUMS['chip']
        did_exist = df2.plt.fignum_exists(fnum)
        kwargs.pop('nodraw', None)
        df2.figure(fnum=fnum, docla=True, doclf=True)
        INTERACTIVE_CHIPS = True  # This should always be True
        if INTERACTIVE_CHIPS:
            interact_fn = interact.interact_chip
            interact_fn(back.hs, cx, fnum=fnum, figtitle='Chip View',
                        nodraw=True, **kwargs)
        else:
            viz.show_chip(back.hs, cx, fnum=fnum, figtitle='Chip View')
        back._layout_figures_if(did_exist)

    @drawing
    @profile
    def show_query_result(back, res, tx=None, **kwargs):
        kwargs.pop('nodraw', None)
        if tx is not None:
            fnum = FNUMS['inspect']
            did_exist = df2.plt.fignum_exists(fnum)
            # Interact with the tx\th top index
            res.interact_top_chipres(back.hs, tx, nodraw=True, **kwargs)
        else:
            fnum = FNUMS['res']
            did_exist = df2.plt.fignum_exists(fnum)
            df2.figure(fnum=fnum, docla=True, doclf=True)
            if back.hs.prefs.display_cfg.showanalysis:
                # Define callback for show_analysis
                res.show_analysis(back.hs, fnum=fnum, figtitle=' Analysis View')
            else:
                res.show_top(back.hs, fnum=fnum, figtitle='Query View ')
        back._layout_figures_if(did_exist)

    @drawing
    @profile
    def show_single_query(back, res, cx, **kwargs):
        # Define callback for show_analysis
        fnum = FNUMS['inspect']
        did_exist = df2.plt.fignum_exists(fnum)
        kwargs.pop('nodraw', None)
        df2.figure(fnum=fnum, docla=True, doclf=True)
        interact.interact_chipres(back.hs, res, cx=cx, fnum=fnum,
                                  nodraw=True, **kwargs)
        back._layout_figures_if(did_exist)

    @drawing
    @profile
    def show_nx(back, nx, sel_cxs=[], **kwargs):
        # Define callback for show_analysis
        fnum = FNUMS['name']
        kwargs.pop('nodraw', None)
        df2.figure(fnum=fnum, docla=True, doclf=True)
        interact.interact_name(back.hs, nx, sel_cxs, back.select_cx,
                               fnum=fnum, nodraw=True, **kwargs)

    #----------------------
    # Work Functions
    #----------------------

    def get_selected_gx(back):
        'selected image index'
        if back.selection is None:
            return None
        type_ = back.selection['type_']
        if type_ == 'gx':
            gx = back.selection['index']
        elif type_ == 'cx':
            cx = back.selection['index']
            gx = back.hs.tables.cx2_gx(cx)
        else:
            return None
        return gx

    def get_selected_cx(back, cid=None):
        'selected chip index'
        if cid is not None:
            try:
                cx = back.hs.cid2_cx(cid)
                return cx
            except IndexError as ex:
                logger.exception("Invalid chip id %r", cid)
                msg = 'Query qcid=%d does not exist / is invalid' % cid
                raise AssertionError(msg)
        if back.selection is None:
            return None
        type_ = back.selection['type_']
        if type_ == 'cx':
            cx = back.selection['index']
        if type_ == 'gx':
            cx = back.selection['sub']
        return cx

    def update_window_title(back):
        if back.hs is None:
            title = 'Hotspotter - NULL database'
        elif back.hs.dirs is None:
            title = 'Hotspotter - invalid database'
        else:
            db_dir = back.hs.dirs.db_dir
            db_name = split(db_dir)[1]
            title = f'Hotspotter - {db_name} - {db_dir}'
        back.windowTitleSignal.emit(title)

    def connect_api(back, hs):
        logger.info("Connecting HotSpotter API")
        back.hs = hs
        if hs.tables is not None:
            hs.register_backend(back)
            back.populate_tables(res=False)
            back.setEnabledSignal.emit(True)
            back.clear_selection()
            back.update_window_title()
            back.apiConnectedSignal.emit()
        else:
            back.setEnabledSignal.emit(False)
        #back.database_loaded.emit()

    #--------------------------------------------------------------------------
    # Populate functions
    #--------------------------------------------------------------------------

    @profile
    def _populate_table(back, tblname, extra_cols={},
                        index_list=None, prefix_cols=[]):
        logger.debug("Populating table %r", tblname)
        headers = back.table_headers[tblname]
        editable = back.table_editable[tblname]
        if tblname == 'cxs':  # in ['cxs', 'res']: TODO props in restable
            prop_keys = list(back.hs.tables.prop_dict.keys())
        else:
            prop_keys = []
        col_headers, col_editable = make_table_header_lists(
            headers,
            editable,
            prop_keys,
        )
        if index_list is None:
            index_list = back.hs.get_valid_indexes(tblname)
        # Prefix datatup
        prefix_datatup = [[prefix_col.get(header, 'error')
                           for header in col_headers]
                          for prefix_col in prefix_cols]
        body_datatup = back.hs.get_datatup_list(tblname, index_list,
                                                col_headers, extra_cols)
        datatup_list = prefix_datatup + body_datatup
        # Populate with fancy headers.
        col_fancyheaders = [back.fancy_headers[key]
                            if key in back.fancy_headers else key
                            for key in col_headers]
        datatup_list = filter_table_rows(
            col_fancyheaders,
            datatup_list,
            back.table_filters.get(tblname, {}),
        )
        row_list = list(range(len(datatup_list)))
        back.populateSignal.emit(tblname, col_fancyheaders, col_editable,
                                 row_list, datatup_list)

    def get_table_filters(back, tblname, headers=None):
        conditions = dict(back.table_filters.get(tblname, {}))
        if headers is None:
            return conditions
        return {
            header: condition
            for header, condition in conditions.items()
            if header in headers
        }

    def resolve_table_header(back, fancy_header):
        return back.reverse_fancy.get(fancy_header, fancy_header)

    def get_table_column(back, tblname, header):
        return back.table_headers[tblname].index(header)

    def set_table_filters(back, tblname, headers, conditions):
        normalized = {
            header: condition
            for header, raw_condition in conditions.items()
            for condition in [normalize_table_filter(raw_condition)]
            if condition is not None and header in headers
        }
        compile_table_filters(headers, normalized)
        back.table_filters[tblname] = normalized
        populate = {
            'gxs': back.populate_image_table,
            'cxs': back.populate_chip_table,
            'nxs': back.populate_name_table,
            'res': back.populate_result_table,
        }[tblname]
        populate()

    def populate_image_table(back, **kwargs):
        back._populate_table('gxs', **kwargs)

    def populate_name_table(back, **kwargs):
        back._populate_table('nxs', **kwargs)

    def populate_chip_table(back, **kwargs):
        back._populate_table('cxs', **kwargs)

    def populate_result_table(back, **kwargs):
        res = back.current_res
        if res is None:
            # Clear the table instead
            logger.debug("No results available")
            back._populate_table('res', index_list=[])
            return
        top_cxs = res.topN_cxs(back.hs, N='all')
        qcx = res.qcx
        # The ! mark is used for ascii sorting. TODO: can we work arround this?
        prefix_cols = [{'rank': '!Query',
                        'score': '---',
                        'name': back.hs.cx2_name(qcx),
                        'cid': back.hs.cx2_cid(qcx), }]
        extra_cols = {
            'score':  lambda cxs:  [res.cx2_score[cx] for cx in iter(cxs)],
        }
        back._populate_table('res', index_list=top_cxs,
                             prefix_cols=prefix_cols,
                             extra_cols=extra_cols,
                             **kwargs)

    def populate_tables(back, image=True, chip=True, name=True, res=True):
        if image:
            back.populate_image_table()
        if chip:
            back.populate_chip_table()
        if name:
            back.populate_name_table()
        if res:
            back.populate_result_table()

    def append_header(back, tblname, header, editable=False):
        try:
            pos = back.table_headers[tblname].index(header)
            logger.debug("%s_TBL already has header=%r at pos=%s", tblname, header, pos)
        except ValueError:
            back.table_headers[tblname].append(header)

    #--------------------------------------------------------------------------
    # Helper functions
    #--------------------------------------------------------------------------

    def get_work_directory(back):
        return params.get_workdir()

    def get_preferences(back):
        return back.hs.prefs

    def get_hotspotter(back):
        return back.hs

    def get_selected_chip_context(back, cid=None):
        cx = back.get_selected_cx(cid)
        if cx is None:
            return None
        return {
            'cx': cx,
            'gx': back.hs.tables.cx2_gx[cx],
            'roi': back.hs.tables.cx2_roi[cx],
            'theta': back.hs.tables.cx2_theta[cx],
        }

    #--------------------------------------------------------------------------
    # Selection Functions
    #--------------------------------------------------------------------------

    @slot_(int)
    @blocking
    @profile
    def select_gx(back, gx, cx=None, show=True, **kwargs):
        # Table Click -> Image Table
        nodraw = kwargs.pop('nodraw', False)
        kwargs.pop('dodraw', None) # TODO: temp fix query image select
        show_chip_splash = kwargs.pop('show_chip_splash', True)
        autoselect_chips = False
        if autoselect_chips and cx is None:
            cxs = back.hs.gx2_cxs(gx)
            if len(cxs > 0):
                cx = cxs[0]
        sel_cxs = [] if cx is None else [cx]
        back.selection = {'type_': 'gx', 'index': gx, 'sub': cx}
        if show:
            if cx is None:
                if show_chip_splash:
                    back.show_splash(FNUMS['chip'], 'Chip', dodraw=False)
            else:
                back.show_chip(cx, dodraw=False, nodraw=True, **kwargs)
            back.show_image(gx, sel_cxs, dodraw=False, nodraw=True, **kwargs)
            if not nodraw:
                df2.draw()

    @slot_(int)
    def select_cid(back, cid, **kwargs):
        # Table Click -> Chip Table
        cx = back.hs.cid2_cx(cid)
        gx = back.hs.cx2_gx(cx)
        back.select_gx(gx, cx=cx, **kwargs)

    @slot_(int)
    def select_cx(back, cx, **kwargs):
        gx = back.hs.cx2_gx(cx)
        back.select_gx(gx, cx=cx, **kwargs)

    @slot_(int)
    def select_nx(back, nx):
        back.show_nx(nx)

    @slot_(str)
    def select_name(back, name):
        name = str(name)
        nx = np.where(back.hs.tables.nx2_name == name)[0]
        back.select_nx(nx)

    @slot_(int)
    def select_res_cid(back, cid, **kwargs):
        # Table Click -> Chip Table
        cx = back.hs.cid2_cx(cid)
        gx = back.hs.cx2_gx(cx)
        back.select_gx(gx, cx=cx, dodraw=False, nodraw=True, **kwargs)
        back.show_single_query(back.current_res, cx, **kwargs)

    #--------------------------------------------------------------------------
    # Misc Slots
    #--------------------------------------------------------------------------

    @slot_(str)
    def backend_print(back, msg):
        logger.info("%s", msg)

    @slot_()
    def clear_selection(back, **kwargs):
        back.selection = None
        back.show_splash(FNUMS['image'], 'Image', dodraw=False)
        back.show_splash(FNUMS['chip'], 'Chip', dodraw=False)
        back.show_splash(FNUMS['res'], 'Results', **kwargs)

    @slot_()
    @blocking
    def default_preferences(back):
        # Button Click -> Preferences Defaults
        # TODO: Propogate changes back to back.edit_prefs.ui
        back.hs.default_preferences()
        back.hs.prefs.save()

    @slot_(int, str, str)
    @blocking
    @profile
    def change_chip_property(back, cid, key, val):
        # Table Edit -> Change Chip Property
        # RCOS TODO: These function should take the type of the variable as an
        # arugment as well. (Guifront tries to automatically interpret the
        # variable type by its value and it will get stuck on things like
        # 'True'. Is that a string or a bool? I don't know. We should tell it.)
        key, val = list(map(str, (key, val)))
        logger.info("Changing chip property cid=%r key=%r val=%r", cid, key, val)
        cx = back.hs.cid2_cx(cid)
        if key in ['name', 'matching_name']:
            back.hs.change_name(cx, val)
        else:
            back.hs.change_property(cx, key, val)
        back.populate_tables(image=False)

    @slot_(int, str, str)
    @blocking
    @profile
    def alias_name(back, nx, key, val):
        key, val = list(map(str, (key, val)))
        logger.info("Aliasing name nx=%r key=%r val=%r", nx, key, val)
        if key in ['name']:
            # TODO: Add option to change name if alias fails
            back.hs.alias_name(nx, val)
        back.populate_tables(image=False)

    @slot_(int, str, bool)
    @blocking
    def change_image_property(back, gx, key, val):
        # Table Edit -> Change Image Property
        key, val = str(key), bool(val)
        logger.info("Changing image property gx=%r key=%r val=%r", gx, key, val)
        if key in ['aif']:
            back.hs.change_aif(gx, val)
        back.populate_image_table()

    #--------------------------------------------------------------------------
    # File Slots
    #--------------------------------------------------------------------------

    @slot_()
    @blocking
    def new_database(back, new_dbdir=None):
        # File -> New Database
        if new_dbdir is not None:
            logger.info("Creating new database directory %r", new_dbdir)
            util.ensurepath(new_dbdir)
            back.open_database(new_dbdir)
        else:
            logger.info("Aborted new database creation")

    @slot_()
    @blocking
    def open_database(back, db_dir=None):
        # File -> Open Database
        try:
            # Use the same args in a new (opened) database
            args = params.args
            if db_dir is None:
                logger.info("Aborted database open because no directory was supplied")
                return None
            logger.info("User selected database %s", db_dir)
            if not db_dir:
                return
            # Try and load db
            if args is not None:
                args.dbdir = db_dir
            hs = HotSpotterAPI.HotSpotter(args=args, db_dir=db_dir)
            hs.load(load_all=False)
            # Write to cache and connect if successful
            io.global_cache_write('db_dir', db_dir)
            back.connect_api(hs)
        except Exception as ex:
            _report_backend_exception(
                back, 'Open database failed',
                'Aborting open database', ex)
            return None
        return hs

    @slot_()
    @blocking
    def save_database(back):
        # File -> Save Database
        back.hs.save_database()


    @slot_()
    @blocking
    def import_images_from_file(back, fpath_list=None):
        # File -> Import Images From File
        if not fpath_list:
            logger.info("No image files selected for import")
            return
        back.hs.add_images(fpath_list)
        back.populate_image_table()

    @slot_()
    @blocking
    def import_images_from_dir(back, img_dpath=None):
        # File -> Import Images From Directory
        if not img_dpath:
            logger.info("No image directory selected for import")
            return
        logger.info("Selected image directory %r", img_dpath)
        fpath_list = util.list_images(img_dpath, fullpath=True)
        back.hs.add_images(fpath_list)
        back.populate_image_table()


    #--------------------------------------------------------------------------
    # Action menu slots
    #--------------------------------------------------------------------------

    @slot_()
    @blocking
    def new_prop(back, newprop=None):
        # Action -> New Chip Property
        if not newprop:
            logger.info("Aborted property creation because no name was supplied")
            return
        back.hs.add_property(newprop)
        back.populate_chip_table()
        back.populate_result_table()
        logger.info("Added chip property %r", newprop)

    @slot_()
    @blocking
    @profile
    def add_chip(back, gx=None, roi=None):
        # Action -> Add ROI
        if gx is None:
            gx = back.get_selected_gx()
        if gx is None:
            back.informationSignal.emit(
                'Add Chip', 'Select an image before adding a chip')
            return
        if roi is None:
            logger.info("ROI was not supplied. Not adding chip")
            return
        cx = back.hs.add_chip(gx, roi)  # NOQA
        back.populate_tables()
        # RCOS TODO: Autoselect should be an option
        #back.select_gx(gx, cx)
        back.select_gx(gx)
        cid = back.hs.cx2_cid(cx)
        return cid

    @slot_()
    @blocking
    @profile
    def query(back, cid=None, tx=None, **kwargs):
        # Action -> Query

        with util.Indent('[back.prequery]'):
            logger.info("Query requested cid=%r kwargs=%r", cid, kwargs)
            cx = back.get_selected_cx(cid)
            logger.debug("Resolved query cx=%r", cx)
            if cx is None:
                back.informationSignal.emit(
                    'Query', 'Cannot query. No chip selected')
                return
        with util.Indent('[back.query]'):
            try:
                res = back.hs.query(cx, **kwargs)
            except Exception as ex:
                _report_backend_exception(
                    back, 'Query failed',
                    'The query could not be completed', ex)
                return None
        with util.Indent('[back.postquery]'):
            if isinstance(res, str):
                back.operationFailedSignal.emit('Query failed', res)
                return
            try:
                back.current_res = res
                back.populate_result_table()
                logger.info("Finished query")
                # Show results against test chip index (tx)
                back.show_query_result(res, tx)
            except Exception as ex:
                _report_backend_exception(
                    back, 'Query display failed',
                    'The query completed, but results could not be displayed',
                    ex)
                return res
        return res

    @slot_()
    @blocking
    @profile
    def reselect_roi(back, cid=None, roi=None, **kwargs):
        # Action -> Reselect ROI
        logger.info("Reselect ROI requested")
        cx = back.get_selected_cx(cid)
        if cx is None:
            back.informationSignal.emit(
                'Reselect ROI', 'Cannot reselect ROI. No chip selected')
            return
        gx = back.hs.tables.cx2_gx[cx]
        if roi is None:
            logger.info("ROI was not supplied. Not changing chip")
            return
        back.hs.change_roi(cx, roi)
        back.hs.save_database()
        back.populate_tables()
        back.select_gx(gx, cx, **kwargs)
        logger.info("Reselected ROI=%r", roi)

    @slot_()
    @blocking
    @profile
    def reselect_ori(back, cid=None, theta=None, **kwargs):
        # Action -> Reselect ORI
        cx = back.get_selected_cx(cid)
        if cx is None:
            back.informationSignal.emit(
                'Reselect Orientation',
                'Cannot reselect orientation. No chip selected',
            )
            return
        gx = back.hs.tables.cx2_gx[cx]
        if theta is None:
            logger.info("Orientation was not supplied. Not changing chip")
            return
        back.hs.change_theta(cx, theta)
        back.hs.save_database()
        back.populate_tables()
        back.select_gx(gx, cx, **kwargs)
        logger.info("Reselected theta=%r", theta)

    @slot_()
    @blocking
    @profile
    def delete_chip(back):
        # Action -> Delete Chip
        # RCOS TODO: Are you sure?
        cx = back.get_selected_cx()
        if cx is None:
            back.informationSignal.emit(
                'Delete Chip', 'Cannot delete chip. No chip selected')
            return
        gx = back.hs.cx2_gx(cx)
        back.hs.delete_chip(cx)
        back.populate_tables()
        back.select_gx(gx)
        logger.info("Deleted chip cx=%r", cx)

    @slot_()
    @blocking
    @profile
    def delete_image(back, gx=None):
        if gx is None:
            gx = back.get_selected_gx()
        if gx is None:
            back.informationSignal.emit(
                'Delete Image', 'Cannot delete image. No image selected')
            return
        back.clear_selection()
        back.hs.delete_image(gx)
        back.populate_tables()
        logger.info("Deleted image gx=%r", gx)

    @slot_()
    @blocking
    @profile
    def select_next(back):
        # Action -> Next
        msg = select_next_image(back)
        if msg is not None:
            back.informationSignal.emit('Select Next', msg)

    @slot_()
    @blocking
    @profile
    def select_next_unannotated(back):
        # Action -> Next Unannotated
        msg = select_next_image(back, next_unannotated=True)
        if msg is not None:
            back.informationSignal.emit('Select Next Unannotated', msg)

    #--------------------------------------------------------------------------
    # Batch menu slots
    #--------------------------------------------------------------------------

    @slot_()
    @blocking
    def precompute_feats(back):
        # Batch -> Precompute Feats
        back.hs.update_samples()
        back.hs.refresh_features()
        back.populate_chip_table()

    @slot_()
    @blocking
    def precompute_queries(back):
        # Batch -> Precompute Queries
        # TODO:
        #http://stackoverflow.com/questions/15637768/
        # pyqt-how-to-capture-output-of-pythons-interpreter-
        # and-display-it-in-qedittext
        #import matching_functions as mf
        #import DataStructures as ds
        #import match_chips3 as mc3
        back.precompute_feats()
        valid_cx = back.hs.get_valid_cxs()
        #if back.params.args.quiet:
            #mc3.print_off()
            #ds.print_off()
            #mf.print_off()
        fmtstr = util.progress_str(len(valid_cx), '[back*] Query qcx=%r: ')
        for count, qcx in enumerate(valid_cx):
            sys.stdout.write(fmtstr % (qcx, count))
            back.hs.query(qcx, dochecks=False)
            if count % 100 == 0:
                sys.stdout.write('\n ...')
        sys.stdout.write('\n ...')
        #mc3.print_on()
        #ds.print_on()
        #mf.print_on()

    #--------------------------------------------------------------------------
    # Help menu slots
    #--------------------------------------------------------------------------

    @slot_()
    def view_docs(back):
        from hscom import cross_platform as cplat
        hsdir = io.get_hsdir()
        pdf_dpath = join(hsdir, '_doc')
        pdf_fpath = join(pdf_dpath, 'HotSpotterUserGuide.pdf')
        cplat.startfile(pdf_fpath)

    @slot_()
    def view_database_dir(back):
        # Help -> View Directory Slots
        back.hs.vdd()

    @slot_()
    def view_computed_dir(back):
        back.hs.vcd()

    @slot_()
    def view_global_dir(back):
        back.hs.vgd()

    @slot_()
    def delete_cache(back):
        # Help -> Delete Directory Slots
        back.invalidate_result()
        df2.close_all_figures()
        back.hs.delete_cache()
        back.populate_result_table()

    @slot_()
    def delete_global_prefs(back):
        # RCOS TODO: Are you sure?
        df2.close_all_figures()
        back.hs.delete_global_prefs()

    @slot_()
    def delete_queryresults_dir(back):
        # RCOS TODO: Are you sure?
        df2.close_all_figures()
        back.invalidate_result()
        back.hs.delete_queryresults_dir()
        back.populate_result_table()

    def invalidate_result(back):
        back.current_res = None

    @slot_()
    @blocking
    def detect_dupimg(back):
        back.hs.dbg_duplicate_images()
