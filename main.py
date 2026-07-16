#!/usr/bin/env python3
# HotSpotter main script.
# Runs the HotSpotter GUI.
# Import as few things as possible at module scope because multiprocessing workers may import this module again.

import multiprocessing

def dependencies_for_myprogram():
    """Expose hidden imports to PyInstaller."""
    from scipy.sparse.csgraph import _validation  # NOQA
    from scipy.special import _ufuncs_cxx  # NOQA

def postload_args_process(hs, back):
    import logging
    from hscom import params

    logger = logging.getLogger(__name__)

    # Run startup commands.
    if params.args.autoquery:
        back.precompute_queries()

    qcid_list = params.args.query
    tx_list = params.args.txs
    qfx_list = params.args.qfxs
    cid_list = params.args.cids

    res = None

    if qcid_list:
        qcid = qcid_list[0]
        tx = tx_list[0] if tx_list else None

        try:
            res = back.query(qcid, tx)
            back.select_cid(qcid, show=False)

            if cid_list:
                cx = hs.cid2_cx(cid_list[0])

                if qfx_list:
                    qfx = qfx_list[0]
                    mx = res.get_match_index(hs, cx, qfx)
                    res.interact_chipres(hs,cx,fnum=4,mx=mx,)
                    res.show_nearest_descriptors(hs,qfx,)
                else:
                    res.interact_chipres(hs,cx,fnum=4,)

        except AssertionError:
            logger.exception("Startup query failed")

    selgxs = params.args.selgxs

    if selgxs:
        back.select_gx(selgxs[0])

    selnxs = params.args.selnxs

    if selnxs:
        name = hs.nx2_name(selnxs[0])
        back.select_name(name)

    selcids = params.args.selcids

    if selcids:
        selcxs = hs.cid2_cx(selcids)
        back.select_cx(selcxs[0])

    return locals()


def main():
    from hscom.logging_utils import configure_logging
    configure_logging(log_dir="logs", debug=True, quiet=False)

    from hsdev import test_api

    hs, back, app, is_root = test_api.main_init()

    postload_locals = postload_args_process(hs,back,)

    res = postload_locals["res"]

    test_api.main_loop(app,is_root,back,)
    return 0


if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
