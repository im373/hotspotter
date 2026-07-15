# HotSpotter port notes:
# Split dynamic reload helpers out of hscom.__common__.

import importlib
import logging
import sys

logger = logging.getLogger(__name__)


def reload_module(module_or_name):
    """Reload a module object or an already-imported module name."""
    module = (sys.modules[module_or_name]
              if isinstance(module_or_name, str) else module_or_name)
    logger.debug("Reloading module %s", module.__name__)
    return importlib.reload(module)


def make_reloader(module_name, module_prefix=None):
    """Return a legacy-compatible no-arg reloader for a module name."""
    def reload_current_module():
        prefix = '' if module_prefix is None else module_prefix + ' '
        logger.info("%sreloading %s", prefix, module_name)
        return reload_module(module_name)
    return reload_current_module
