import functools
import inspect
import logging
import logging.config
from pathlib import Path
import textwrap
import warnings


logger = logging.getLogger(__name__)


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


def DEPRECATED(func):
    """Warn and log whenever a deprecated function is called."""
    func_name = f'{func.__module__}.{func.__qualname__}'

    try:
        func_source = textwrap.dedent(inspect.getsource(func)).rstrip()
    except (OSError, TypeError):
        func_source = '<source unavailable>'

    @functools.wraps(func)
    def deprecated_wrapper(*args, **kwargs):
        caller = inspect.stack()[1]
        warn_msg = (
            f'Deprecated call to {func_name} from '
            f'{caller.filename}:{caller.lineno} in {caller.function}()'
        )
        log = logging.getLogger(func.__module__)
        log.warning("%s", warn_msg)
        log.debug('Deprecated function source for %s:\n%s', func_name, func_source)
        warnings.warn(warn_msg, category=DeprecationWarning, stacklevel=2)
        return func(*args, **kwargs)

    return deprecated_wrapper


# Compatibility alias for legacy misspelling. New code should use DEPRECATED.
DEPRICATED = DEPRECATED


def configure_logging(
    log_dir="logs",
    debug=False,
    quiet=False,
):
    """Configure application logging.

    This function should be called once by the application entry point.
    """
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    log_path = log_dir / "hotspotter.log"


    if quiet:
        console_level = "WARNING"
        file_level = "INFO"
    elif debug:
        console_level = "DEBUG"
        file_level = "DEBUG"
    else:
        console_level = "INFO"
        file_level = "INFO"

    config = {
        "version": 1,

        # Preserve loggers created before configuration.
        "disable_existing_loggers": False,

        "formatters": {
            "standard": {
                "format": (
                    "%(asctime)s "
                    "%(levelname)-8s "
                    "%(name)s: "
                    "%(message)s"
                ),
                "datefmt": "%H:%M:%S",
            },
        },

        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": console_level,
                "formatter": "standard",
                "stream": "ext://sys.stdout",
            },

            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": file_level,
                "formatter": "standard",
                "filename": str(log_path),
                "maxBytes": 5_000_000,
                "backupCount": 5,
                "encoding": "utf-8",
            },
        },

        "root": {
            "level": "DEBUG",
            "handlers": [
                "console",
                "file",
            ],
        },
    }

    logging.config.dictConfig(config)

    return log_path
