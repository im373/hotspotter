# HotSpotter port notes:
# Updated shared compatibility helpers for Python 3, NumPy 2, and Windows paths.
# Removed legacy log handler setup; logging is configured through hscom.logging_utils.
# Delegated profiling, dynamic reload, and Matplotlib setup to focused hscom modules.

import builtins
import logging
import sys

from .dev_utils import make_reloader
from .logging_utils import DEPRECATED
from .mpl_utils import configure_matplotlib
from .profiling import profile

__MODULE_LIST__ = []


def argv_flag(name, default):
    # TODO Merge util's argv stuff here or merge this there?
    # Or split it into sepearate top-level module?
    if name.find('--') == 0:
        name = name[2:]
    if '--' + name in sys.argv and default is False:
        return True
    if '--no' + name in sys.argv and default is True:
        return False
    return default

__QUIET__      = argv_flag('--quiet', False)
__AGGROFLUSH__ = argv_flag('--aggroflush', False)
__DEBUG__      = argv_flag('--debug', False)
__INDENT__     = argv_flag('--indent', True)

 #|  %(name)s            Name of the logger (logging channel)
 #|  %(levelno)s         Numeric logging level for the message (DEBUG, INFO,
 #|                      WARNING, ERROR, CRITICAL)
 #|  %(levelname)s       Text logging level for the message ("DEBUG", "INFO",
 #|                      "WARNING", "ERROR", "CRITICAL")
 #|  %(pathname)s        Full pathname of the source file where the logging
 #|                      call was issued (if available)
 #|  %(filename)s        Filename portion of pathname
 #|  %(module)s          Module (name portion of filename)
 #|  %(lineno)d          Source line number where the logging call was issued
 #|                      (if available)
 #|  %(funcName)s        Function name
 #|  %(created)f         Time when the LogRecord was created (time.time()
 #|                      return value)
 #|  %(asctime)s         Textual time when the LogRecord was created
 #|  %(msecs)d           Millisecond portion of the creation time
 #|  %(relativeCreated)d Time in milliseconds when the LogRecord was created,
 #|                      relative to the time the logging module was loaded
 #|                      (typically at application startup time)
 #|  %(thread)d          Thread ID (if available)
 #|  %(threadName)s      Thread name (if available)
 #|  %(process)d         Process ID (if available)
 #|  %(message)s         The result of record.getMessage(), computed just as
 #|                      the record is emitted

def add_logging_handler(handler, default_format=True):
    """Attach an extra handler to the application root logger.

    The main entry point owns logging configuration through
    hscom.logging_utils.configure_logging(). This helper remains only for
    legacy GUI code that needs to mirror log records into a widget.
    """
    if default_format:
        logformat = '[%(asctime)s]%(message)s'
        timeformat = '%H:%M:%S'
        formatter = logging.Formatter(logformat, timeformat)
        handler.setLevel(logging.DEBUG)
        handler.setFormatter(formatter)
    logging.getLogger().addHandler(handler)

@DEPRECATED
def create_logger():
    """Legacy no-op.

    Logging is configured once by main.py via hscom.logging_utils.
    """
    return logging.getLogger()

@DEPRECATED
def get_modules():
    if __INDENT__:
        return __MODULE_LIST__
    else:
        return []

@DEPRECATED
def init(module_name, module_prefix='[???]', DEBUG=None, initmpl=False):
    # implicitly imports a set of standard functions into hotspotter modules
    # makes keeping track of printing much easier
    global __MODULE_LIST__
    module = sys.modules[module_name]
    __MODULE_LIST__.append(module)
    logger = logging.getLogger(module_name)

    if __DEBUG__:
        builtins.print('[common] import %s  # %s' % (module_name, module_prefix))

    # Define reloading function
    rrr = make_reloader(module_name, module_prefix)

    # Define log_print
    if __DEBUG__:
        def log_print(msg):
            logger.info(f'{module_prefix}{msg}')

        def log_print_(msg):
            logger.info(f'{module_prefix}{str(msg).rstrip()}')
    else:
        if __AGGROFLUSH__:
            def log_print_(msg):
                logger.info(f'{str(msg).rstrip()}')
        else:
            def log_print_(msg):
                logger.info(f'{str(msg).rstrip()}')
        def log_print(msg):
            logger.info(f'{msg}')

    def noprint(msg):
        pass

    # Define print switches
    # Closures are cool
    def print_on():
        if not module in __MODULE_LIST__:
            __MODULE_LIST__.append(module)  # SO HACKY
        module.print = log_print
        module.print_ = log_print_

    def print_off():
        if module in __MODULE_LIST__:
            __MODULE_LIST__.remove(module)  # SO HACKY
        module.print = noprint
        module.print_ = noprint

    # ACTUALLY SET PRINT:
    # FIXME we dont actually have to overwrite the name in this module
    print  = log_print
    print_ = log_print_

    if DEBUG is None:
        return print, print_, print_on, print_off, rrr, profile

    # Define a printdebug function
    if DEBUG:
        def printDBG(msg):
            logger.debug(f'{module_prefix} DEBUG {msg}')
    else:
        def printDBG(msg):
            pass

    # Initialize matplotlib if requested
    # if initmpl:
    #     toolbar = 'None' if ('--notoolbar' in sys.argv or '--devmode' in sys.argv) else 'toolbar2'
    #     configure_matplotlib(toolbar=toolbar, quiet=__QUIET__)

    return print, print_, print_on, print_off, rrr, profile, printDBG
