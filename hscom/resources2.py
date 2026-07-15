
# HotSpotter port notes:
# Replaced hscom.__common__ hooks with logging/dev helpers.

import logging
# Python
import psutil
import os
# HotSpotter
from . import helpers as util
from .dev_utils import make_reloader

logger = logging.getLogger(__name__)
rrr = make_reloader(__name__, '[resources]')
printDBG = logger.debug


def peak_memory():
    import resource
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def current_memory_usage():
    meminfo = psutil.Process(os.getpid()).get_memory_info()
    rss = meminfo[0]  # Resident Set Size / Mem Usage
    vms = meminfo[1]  # Virtual Memory Size / VM Size  # NOQA
    return rss


def num_cpus():
    return psutil.NUM_CPUS


def available_memory():
    return psutil.virtual_memory().available


def total_memory():
    return psutil.virtual_memory().total


def used_memory():
    return total_memory() - available_memory()


def memstats():
    logger.info("total = %s", util.byte_str2(total_memory()))
    logger.info("available = %s", util.byte_str2(available_memory()))
    logger.info("used = %s", util.byte_str2(used_memory()))
    logger.info("current = %s", util.byte_str2(current_memory_usage()))

if __name__ == '__main__':
    memstats()


#psutil.virtual_memory()
#psutil.swap_memory()
#psutil.disk_partitions()
#psutil.disk_usage("/")
#psutil.disk_io_counters()
#psutil.net_io_counters(pernic=True)
#psutil.get_users()
#psutil.get_boot_time()
#psutil.get_pid_list()
