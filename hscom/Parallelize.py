# HotSpotter port notes:
# Updated shared compatibility helpers for Python 3, NumPy 2, and Windows paths.
# Replaced hscom.__common__ hooks with logging/profiling/dev helpers.

# http://docs.python.org/2/library/multiprocessing.html

# Python

from os.path import exists, dirname, split
import logging
import multiprocessing
import os
import sys
# Hotspotter
from . import helpers as util
from .dev_utils import make_reloader
from .profiling import profile

logger = logging.getLogger(__name__)
rrr = make_reloader(__name__, '[parallel]')
printDBG = logger.debug


@profile
def _calculate(func, args):
    printDBG("* %s calculating...", multiprocessing.current_process().name)
    result = func(*args)
    #arg_names = func.func_code.co_varnames[:func.func_code.co_argcount]
    #arg_list  = [n+'='+str(v) for n,v in zip(arg_names, args)]
    #arg_str = '\n    *** '+str('\n    *** '.join(arg_list))
    printDBG(
        " * %s finished:\n    ** %s",
        multiprocessing.current_process().name,
        func.__name__,
    )
    return result


@profile
def _worker(input, output):
    printDBG("START WORKER input=%r output=%r", input, output)
    for func, args in iter(input.get, 'STOP'):
        printDBG("worker will calculate %r", func)
        result = _calculate(func, args)
        printDBG("worker has calculated %r", func)
        output.put(result)
        #printDBG('[parallel] worker put result in queue.')
    #printDBG('[parallel] worker is done input=%r output=%r' % (input, output))


@profile
def parallel_compute(func=None, arg_list=[], num_procs=None, lazy=True, args=None,
                     common_args=[], output_dir=None):
    if args is not None and num_procs is None:
        num_procs = args.num_procs
    elif num_procs is None:
        num_procs = max(1, int(multiprocessing.cpu_count() / 2))
    # Generate a list of tasks to send to the parallel processes
    task_list = make_task_list(func, arg_list, lazy=lazy,
                               common_args=common_args, output_dir=output_dir)
    nTasks = len(task_list)
    if nTasks == 0:
        logger.info("No %s tasks left to compute", func.__name__)
        return None
    # Do not execute small tasks in parallel
    if nTasks < num_procs / 2 or nTasks == 1:
        num_procs = 1
    num_procs = min(num_procs, nTasks)
    task_lbl = func.__name__ + ': '
    try:
        ret = parallelize_tasks(task_list, num_procs, task_lbl)
    except Exception as ex:
        sys.stdout.flush()
        logger.exception("Problem while parallelizing task: %r", ex)
        logger.error("task_list:")
        for task in task_list:
            logger.error("  %r", task)
            break
        logger.error("common_args = %r", common_args)
        logger.error("num_procs = %r", num_procs)
        logger.error("task_lbl = %r", task_lbl)
        sys.stdout.flush()
        raise
    return ret


def get_common_paths(output_fpath_list):
    # Takes a list of paths and extracts the common relative paths
    dir_list = [dirname(fpath) for fpath in output_fpath_list]
    fname_list = [split(fpath)[1] for fpath in output_fpath_list]
    unique_dirs = list(set(dir_list))
    return unique_dirs, fname_list


@profile
def make_task_list(func, arg_list, lazy=True, common_args=[], output_dir=None):
    '''
    The input should alawyas be argument 1
    The output should always be argument 2
    '''
    has_output = len(arg_list) >= 2
    append_common = lambda _args: tuple(list(_args) + common_args)
    if not (lazy and has_output):
        # does not check existance
        task_list = [(func, append_common(_args)) for _args in zip(*arg_list)]
        return task_list

    if output_dir is None:
        # Hackish way of getting an output dir for faster exists computation
        output_fpath_list = arg_list[1]
        unique_dirs, output_fname_list = get_common_paths(output_fpath_list)
        if len(unique_dirs) == 1:
            output_dir = unique_dirs[0]
    else:
        # Less hackish
        output_fname_list = arg_list[1]

    if output_dir is not None:
        # This is a faster than checkign for existance individually
        # But all the files need to be in the same directory
        fname_set = set(os.listdir(output_dir))
        exist_list = [fname in fname_set for fname in output_fname_list]
        argiter = zip(exist_list, zip(*arg_list))
        arg_list2 = [append_common(_args) for bit, _args in argiter if not bit]
    else:
        # check existance individually
        arg_list2 = [append_common(_args) for _args in zip(*arg_list) if not exists(_args[1])]
    task_list = [(func, _args) for _args in iter(arg_list2)]
    nSkip = len(list(zip(*arg_list))) - len(arg_list2)
    logger.info("Already computed %s %s tasks", nSkip, func.__name__)
    return task_list


@profile
def parallelize_tasks(task_list, num_procs, task_lbl='', verbose=True):
    '''
    Used for embarissingly parallel tasks, which write output to disk
    '''
    nTasks = len(task_list)
    msg = ('Distributing %d %s tasks to %d processes' % (nTasks, task_lbl, num_procs)
           if num_procs > 1 else
           'Executing %d %s tasks in serial' % (nTasks, task_lbl))
    with util.Timer(msg=msg):
        if num_procs > 1:
            # Parallelize tasks
            return _compute_in_parallel(task_list, num_procs, task_lbl, verbose)
        else:
            return _compute_in_serial(task_list, task_lbl, verbose)


@profile
def _compute_in_serial(task_list, task_lbl='', verbose=True):
    # Serialize Tasks
    result_list = []
    nTasks = len(task_list)
    if verbose:
        mark_progress, end_prog = util.progress_func(nTasks, lbl=task_lbl)
        # Compute each task
        for count, (fn, args) in enumerate(task_list):
            mark_progress(count)
            #sys.stdout.flush()
            result = fn(*args)
            result_list.append(result)
        end_prog()
    else:
        # Compute each task
        for (fn, args) in iter(task_list):
            result = fn(*args)
            result_list.append(result)
        logger.info("done")
    return result_list


@profile
def _compute_in_parallel(task_list, num_procs, task_lbl='', verbose=True):
    '''
    Input: task list: [ (fn, args), ... ]
    '''
    task_queue = multiprocessing.Queue()
    done_queue = multiprocessing.Queue()
    nTasks = len(task_list)
    # queue tasks
    for task in iter(task_list):
        task_queue.put(task)
    # start processes
    proc_list = []
    for i in range(num_procs):
        printDBG("creating process %r", i)
        proc = multiprocessing.Process(target=_worker, args=(task_queue, done_queue))
        proc.daemon = True
        proc.start()
        proc_list.append(proc)
    # wait for results
    printDBG("waiting for results")
    sys.stdout.flush()
    result_list = []
    if verbose:
        mark_progress, end_prog = util.progress_func(nTasks, lbl=task_lbl, spacing=num_procs)
        for count in range(len(task_list)):
            mark_progress(count)
            printDBG("done_queue.get()")
            result = done_queue.get()
            result_list.append(result)
        end_prog()
    else:
        for i in range(nTasks):
            done_queue.get()
        logger.info("done")
    printDBG("stopping children")
    # stop children processes
    for i in range(num_procs):
        task_queue.put('STOP')
    for proc in proc_list:
        proc.join()
    return result_list
    #import time
    #time.sleep(.01)
