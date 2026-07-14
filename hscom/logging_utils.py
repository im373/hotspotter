# hscom/logging_utils.py

import builtins
import logging
import logging.config
from pathlib import Path


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
    elif debug:
        console_level = "DEBUG"
    else:
        console_level = "INFO"

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
                "level": "DEBUG",
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