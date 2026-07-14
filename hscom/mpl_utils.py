# HotSpotter port notes:
# Split Matplotlib runtime setup out of hscom.__common__.

import logging
import multiprocessing

logger = logging.getLogger(__name__)


def configure_matplotlib(
    backend="Qt5Agg",
    toolbar="toolbar2",
    quiet=False,
):
    """Configure Matplotlib for the HotSpotter GUI runtime."""
    import matplotlib
    current_backend = matplotlib.get_backend()

    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("matplotlib.font_manager").setLevel(logging.WARNING)
    if hasattr(matplotlib, "set_loglevel"):
        try:
            matplotlib.set_loglevel("warning")
        except Exception:
            logger.debug("Could not set Matplotlib log level", exc_info=True)

    in_main_process = multiprocessing.current_process().name == "MainProcess"
    if in_main_process and not quiet:
        logger.debug(f"Current Matplotlib backend is {current_backend!r}. Using Matplotlib backend {backend}")

    if current_backend != backend:
        matplotlib.use(backend, force=True)
        current_backend = matplotlib.get_backend()
        if in_main_process and not quiet:
            logger.debug(f"Current Matplotlib backend is {current_backend!r}")

    matplotlib.rcParams["toolbar"] = toolbar
    matplotlib.rc("text", usetex=False)

    for key in list(matplotlib.rcParams.keys()):
        if key.startswith("keymap."):
            matplotlib.rcParams[key] = []
