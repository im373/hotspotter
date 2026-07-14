
import logging

from hscom.dev_utils import make_reloader

logger = logging.getLogger(__name__)
rrr = make_reloader(__name__, '[dev_api]')
printDBG = logger.debug
from . import dev_stats
from . import dev_consistency
from . import dev_reload
from hscom.Printable import DynStruct
from hscom import helpers as util


class DebugAPI(DynStruct):
    def __init__(dbg, hs):
        super(DebugAPI, dbg).__init__(child_exclude_list=['hs'])
        dbg.hs = hs
        for key, val in util.module_functions(dev_consistency):
            printDBG('[devapi] augmenting: ' + str(val))
            dbg.__dict__[key] = val

    def dbstats(dbg):
        return dev_stats.dbstats(dbg.hs)

    def reload(dbg):
        _reload()


def augment_api(hs):
    dbg = DebugAPI(hs)

    hs.dbg = dbg
    return hs


def _reload():
    dev_reload.reload_all_modules()
