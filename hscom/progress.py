"""Progress reporting helpers used by HotSpotter batch operations."""

import logging
import sys


logger = logging.getLogger(__name__)

VALID_PROGRESS_TYPES = ['none', 'dots', 'fmtstr', 'simple']


def simple_progres_func(verbosity, msg, progchar='.'):
    def mark_progress0(*args):
        pass

    def mark_progress1(*args):
        logger.debug("%s", progchar)

    def mark_progress2(*args):
        logger.debug(msg, *args)

    if verbosity not in (0, 1, 2):
        raise ValueError('Unsupported progress verbosity: %r' % verbosity)
    if verbosity == 0:
        mark_progress = mark_progress0
    elif verbosity == 1:
        mark_progress = mark_progress1
    else:
        mark_progress = mark_progress2
    return mark_progress


def progress_func(max_val=0, lbl='Progress: ', mark_after=-1,
                  flush_after=4, spacing=0, line_len=80,
                  progress_type='fmtstr'):
    """Return callbacks that report progress at debug level."""

    def log_progress(message):
        logger.debug("%s", message)

    if progress_type not in VALID_PROGRESS_TYPES:
        raise ValueError('Unsupported progress type: %r' % progress_type)
    if progress_type in ['simple', 'fmtstr'] and max_val < mark_after:
        return lambda count: None, lambda: None
    if progress_type == 'none':
        mark_progress = lambda count: None
    elif progress_type == 'simple':
        mark_progress = lambda count: log_progress(
            f"{lbl}{count + 1}/{max_val}" if max_val else lbl
        )
    elif progress_type == 'dots':
        if spacing > 0:
            def mark_progress_sdot(count):
                count_ = count + 1
                if count_ % spacing == 0 or count_ == max_val:
                    log_progress(f"{lbl}{count_}/{max_val}")
            mark_progress = mark_progress_sdot
        else:
            def mark_progress_dot(count):
                count_ = count + 1
                if count_ % flush_after == 0 or count_ == max_val:
                    log_progress(f"{lbl}{count_}/{max_val}")
            mark_progress = mark_progress_dot
    else:
        def mark_progress_fmtstr(count):
            count_ = count + 1
            if count_ == 1 or count_ == max_val or count_ % flush_after == 0:
                log_progress(f"{lbl}{count_}/{max_val}")
        mark_progress = mark_progress_fmtstr

    if '--aggroflush' in sys.argv:
        base_mark_progress = mark_progress

        def mark_progress_agressive(count):
            base_mark_progress(count)
        mark_progress = mark_progress_agressive

    def end_progress():
        if max_val:
            log_progress(f"{lbl}done {max_val}/{max_val}")

    mark_progress(0)
    return mark_progress, end_progress


def progress_str(max_val, lbl='Progress: '):
    """Return the historical backspace-based progress format string."""
    max_str = str(max_val)
    dnumstr = str(len(max_str))
    fmt_str = lbl + '%' + dnumstr + 'd/' + max_str
    fmt_str = '\b' * (len(fmt_str) - len(dnumstr) + len(max_str)) + fmt_str
    return fmt_str
