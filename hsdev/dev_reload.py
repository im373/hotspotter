
# HotSpotter port notes:
# Replaced hscom.__common__ reload hooks with hscom.dev_utils.

import logging

from hscom.dev_utils import reload_module

logger = logging.getLogger(__name__)


def reload_all_modules():
    logger.info("===========================")
    logger.info("[dev] performing dev_reload")
    logger.info("---------------------------")
    from hotspotter import DataStructures as ds
    from hotspotter import algos
    from hotspotter import load_data2 as ld2
    from hotspotter import chip_compute2 as cc2
    from hotspotter import feature_compute2 as fc2
    from hotspotter import match_chips3 as mc3
    from hotspotter import matching_functions as mf
    from hotspotter import nn_filters
    from hotspotter import report_results2 as rr2
    from hotspotter import voting_rules2 as vr2
    # Common
    from hscom import Parallelize as parallel
    #from hscom import Preferences as prefs
    #from hscom import Printable
    #from hscom import argparse2
    from hscom import cross_platform as cplat
    from hscom import fileio as io
    from hscom import helpers as util
    from hscom import latex_formater
    from hscom import params
    from hscom import tools
    # Viz
    from hsviz import draw_func2 as df2
    from hsviz import extract_patch
    from hsviz import viz
    from hsviz import interact
    from hsviz import allres_viz
    # GUI
    from hsgui import guitools
    from hsgui import guifront
    from hsgui import guiback
    # DEV
    from . import dev_stats
    from . import dev_consistency
    from . import dev_api
    from . import dev_reload
    reload_targets = [
        util, io, cplat, parallel, latex_formater, params, tools,
        ld2, ds, mf, nn_filters, mc3, vr2, cc2, rr2, fc2, algos,
        guitools, guifront, guiback,
        extract_patch, viz, interact, df2, allres_viz,
        dev_stats, dev_consistency, dev_api, dev_reload,
    ]
    for module in reload_targets:
        reload_module(module)

    logger.info("---------------------------")
    logger.info("df2 reset")
    df2.reset()
    logger.info("---------------------------")
    logger.info("[dev] finished dev_reload()")
    logger.info("===========================")
