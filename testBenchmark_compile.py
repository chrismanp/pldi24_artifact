#!/usr/bin/env python3
"""
Test script to measure performance of pbbs and cilk5
"""

import logging
import argparse
import subprocess
import os
import csv
import sys, getopt
import multiprocessing
import time
import shutil
from enum import Enum
from enum import IntEnum

from parse_lazybenchmark_csv import parse_csv

results_file_categories = ["BENCHMARK", "COMPILES", "DATASET", "NUM CORES",
                           "STATUS", "DISABLE_NUMA", "PARALLEL_FRAMEWORK", "TASK_SCHEDULER", "PFOR_MAXGRAINSIZE", "IGNORE_USERS_PFORGRAINSIZE", "TIME(sec)", "ERROR MSG"]

################
# helper classes

class ColName(IntEnum):
    BENCHMARK = 0
    COMPILES = 1
    DATASET = 2
    NUM_CORES = 3
    STATUS = 4
    DISABLE_NUMA=5
    PARALLEL_FRAMEWORK = 6
    TASK_SCHEDULER = 7
    PFORMAXGRAINSIZE = 8
    IGNORE_USER_PFORGAINSIZE = 9
    TIME = 10
    ERROR_MSG = 11

num_cols = len(results_file_categories) # Of output csv file.

compilation_timeout = 6 * 60 # In seconds.
check_benchmark_timout = 6 * 60 # In seconds.

n_iteration = 1

# Used to indicate whether a given benchmark ran successfully, with an error, or
# timed out.
class CmdStatus:
    CORRECT = 1
    INCORRECT = 2
    TIMEOUT = 3

    @staticmethod
    def asString(status):
        if status == CmdStatus.CORRECT:
            return "OK"
        elif status == CmdStatus.INCORRECT:
            return "FAIL"
        elif status == CmdStatus.TIMEOUT:
            return "TIMEOUT"
        return f"Unknown Status: {status}"

class CilkLowering:
    Serial = 0
    LazyD2 = 1
    Nopoll = 2
    SIGUSR = 3
    UIPI = 4
    LazyD0 = 5
    CilkPlus = 6

    cilkLowering2cilk5Arg = {
        Serial: 's',
        LazyD2: 'lf',
        Nopoll: 'ef',
        SIGUSR: 'sf',
        UIPI: 'uif',
        LazyD0: 'uf',
        CilkPlus: 't'
    }

    cilkLowering2Desc = {
        Serial:  "Serial",
        LazyD2: "LazyD with Frequent Polling",
        Nopoll: "LazyD with No Polling",
        SIGUSR: 'SigUserInterupts',
        UIPI: 'HardwareInterupts',
        LazyD0: "LazyD with InFrequent Polling",
        CilkPlus: "OpenCilk"
    }

    asarg = {
        "lazyd2":  LazyD2,
        "lazyd0":  LazyD0,
        "nopoll":  Nopoll,
        "tapir":  CilkPlus,
        "serial":  Serial,
        }

    @staticmethod
    def checkValid(opt):
        if opt not in CilkLowering.cilkLowering2cilk5Arg:
            raise ValueError(f"{opt} not a valid CilkLowering")

    @staticmethod
    def getCilk5Arg(opt):
        CilkLowering.checkValid(opt)
        return CilkLowering.cilkLowering2cilk5Arg[opt]

    @staticmethod
    def getDescription(opt):
        CilkLowering.checkValid(opt)
        return CilkLowering.cilkLowering2Desc[opt]

    @staticmethod
    def strs2enums(opts):
        result = []
        for opt in opts:
            if opt not in CilkLowering.asarg:
                raise ValueError(f"{opt} not a valid lowering method")
            result.append(CilkLowering.asarg[opt])
        return result

class CompilerOptions:
    def __init__(self, task_scheduler, noopt, finergrainsize, cilk_lowering, suffix):
        self.cilk_lowering = cilk_lowering
        self.task_scheduler = task_scheduler
        self.noopt = noopt
        self.finergrainsize = finergrainsize
        self.extension = suffix

    def get_cilklowering_str(self) :
        return CilkLowering.getDescription(self.cilk_lowering)

class LazyBenchmarkOptions(object):
    def __init__(self, compile_only, execute_only, num_cores, num_tests, benchmarks_to_run, cilk_lowering, task_scheduler, noopt, finergrainsize, measure_icache, measure_promotedtask, disable_numa, verbose, dry_run, wait_load):
        self.compile_only = compile_only
        self.execute_only = execute_only
        self.num_cores = num_cores
        self.num_tests = num_tests
        self.benchmarks_to_run = benchmarks_to_run
        self.cilk_lowering = cilk_lowering
        self.task_scheduler = task_scheduler
        self.noopt = noopt
        self.finergrainsize = finergrainsize
        self.measure_icache = measure_icache
        self.measure_promotedtask = measure_promotedtask
        self.disable_numa = disable_numa
        self.verbose = verbose
        self.dry_run = dry_run
        self.wait_load = wait_load

    def get_cilklowering_str(self) :
        return CilkLowering.getDescription(self.cilk_lowering)

    def getCilk5Arg(self):
        return CilkLowering.getCilk5Arg(self.cilk_lowering)

################
# parse command line arguments

# setup command line parsing
parser = argparse.ArgumentParser(description='Compile and Run benchmarks')
parser.add_argument("--compile", action='store_true', help="Only compile benchmark")
parser.add_argument("--num_cores", nargs='+', default=['1'], help="Number of cores used. Default: 1")
parser.add_argument("--num_tests", default=1, type=int, help="Number of runs per test")
parser.add_argument("--execute", action='store_true', help="Only execute benchmark, don't compile")
parser.add_argument("--disable_numa", action='store_true', help="Disable numa when running the benchmark")
parser.add_argument("--icache", action='store_true', help="Run the icache experiment")
parser.add_argument("--parallel_framework", nargs='+',
                    default=['tapir'],
                    choices=['lazyd0', 'lazyd2', 'nopoll', 'serial', 'tapir'],
                    help="What parallel framework to use. Default: tapir")
parser.add_argument("--fg",
                    default=['no'],
                    choices=['yes', 'no', 'both'],
                    help="Use finer grainsize. Only for LazyD and OpenCilk-fg. Default: no")
parser.add_argument("--noopt",
                    default=['no'],
                    choices=['yes', 'no', 'both'],
                    help="Ignore users grainsize.  Default: no")
parser.add_argument("--schedule_tasks",
                    default=["PBBS"],
                    nargs='+',
                    choices=['PRC', 'PRL', 'DELEGATEPRC', 'PRCPRL', 'DELEGATEPRCPRL', 'OPENCILKDEFAULT_FINE', 'PBBS'],
                    help="How to scheduler parallel task in pfor.")
parser.add_argument("--ifile", default="lazybenchmark.csv", help="Input file")
parser.add_argument("-v", "--verbose", action='store_true', help="Verbose")
parser.add_argument("--dryrun", action='store_true', help="Dry run, only print commands that would be executed")
parser.add_argument("--wait_load", default=10, type=int, help="The minimum load to execute the benchmark (Default=10)")

# parse arguments
flags = parser.parse_args()
compile_only = flags.compile
execute_only = flags.execute
num_cores = flags.num_cores
num_tests = flags.num_tests
disable_numa = flags.disable_numa
wait_load = flags.wait_load
finergrainsize = [flags.fg=='yes'] if flags.fg != 'both' else [True, False]
measure_icache = flags.icache
noopt = [flags.noopt=='yes'] if flags.noopt != 'both' else  [True, False]
input_file = flags.ifile
parallel_framework = flags.parallel_framework
task_scheduler = flags.schedule_tasks
verbose = flags.verbose
dry_run = flags.dryrun
cilk_lowering = CilkLowering.strs2enums(parallel_framework)

# display progress (unless doing dryrun or verbose)
def showprogress(msg):
    if dry_run or verbose:
        return
    sys.stderr.write(msg)
    sys.stderr.flush()

# Gets string representation of run status.
def get_run_status_str(run_status):
    if run_status == CmdStatus.CORRECT:
        return "Correct"
    elif run_status == CmdStatus.INCORRECT:
        return "Incorrect"
    else:
        return "Timeout"

def dump_string(str, w, v):
    if w:
        logging.warning(str)
    else:
        logging.debug(str)
    if(v):
        print(str)

# Run a command
# Return status and message
def runcmd(cmd, timeout, error_handler):
    if dry_run:
        dump_string("Command: " + cmd, 0, 1)
        return CmdStatus.CORRECT, "", "", ""
    else:
        dump_string("Command: " + cmd, 0, verbose)

    p_process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        outb, errb = p_process.communicate(timeout)
        dump_string(outb.decode("utf-8"), 0, verbose)
        dump_string(errb.decode("utf-8"), 1, verbose)
        out = str(outb)
        err = str(errb)
        status, error_string = error_handler(p_process, out, err)
        return status, error_string, out, errb
    except subprocess.TimeoutExpired:
        logging.warning("\nCompilation timed out\n")
        p_process.kill()
        return CmdStatus.TIMEOUT, "Timeout", "", ""



def compile_error_handler(p_process, out, err):
    if("Error" in out):
        logging.warning("Compilation failed")
        return CmdStatus.INCORRECT, "Compilation failed"
    else:
        return CmdStatus.CORRECT, ""

def run_error_handler(p_process, out, err):
    if p_process.returncode:
        logging.warning("Benchmark failed to run correctly")
        return CmdStatus.INCORRECT, "Benchmark failed to run correctly"
    else:
        return CmdStatus.CORRECT, ""


# Returns list [1, 8, 16, ..., max_cores]
# Returns [] if specified number of cores is invalid.
def get_test_num_cores(specified_cores):
    max_cores = multiprocessing.cpu_count()
    test_cores = []
    if specified_cores[0] != None:
        string_core = specified_cores[0].split(",")
        for i in string_core:
            if i.isnumeric():
                test_cores.append(int(i))

    if len(test_cores) != 0:
        return test_cores

    test_cores = [1]

    n = 8
    while (n <= max_cores):
        test_cores.append(n)
        n+=8

    if (test_cores[-1] < max_cores):
        test_cores.append(max_cores)

    return test_cores

scheduler2suffix = {'PRC': 'c',
                    'PRL': 'l',
                    'DELEGATEPRC': 'Dc',
                    'PRCPRL': 'cl',
                    'DELEGATEPRCPRL': 'Dcl',
                    'OPENCILKDEFAULT_FINE': 'f',
                    'PBBS': 'p',
                    }
usergrain2suffix = {True: 'y',
                    False: 'n',
                    }
fine2suffix = {True: 'y',
               False: 'n',
               }
lowering2suffix = {CilkLowering.LazyD0: 'uf',
                   CilkLowering.LazyD2: 'lf',
                   CilkLowering.Nopoll: 'ef',
                   CilkLowering.Serial: 's',
                   CilkLowering.CilkPlus: 't',
                   }

def maybeRename(old, new):
    if dry_run:
        dump_string(f"Command: rename {old} -> {new}", 0, 1)
        return
    dump_string(f"Command: rename {old} -> {new}", 0, verbose)
    try:
        os.rename(old, new)
    except OSError as error:
        print(error)


# generates an exe suffix for options.
# Some combinations don't make sense, for those return False
def makeExeSuffix(benchmark, sched, usergrain, fine, lowering):
    if verbose:
        print(benchmark, sched, usergrain, fine, lowering)
    if benchmark == 'cilk5':
        if usergrain or fine:
            return False, ''
        if sched != 'PBBS':
            return False, ''
    elif benchmark == 'pbbs_v2':
        if sched == "OPENCILKDEFAULT_FINE":
            if lowering != CilkLowering.CilkPlus:
                return False, ''
            else:
                if not fine:
                    return False, ''
        if not (sched == 'DELEGATEPRCPRL' or sched == 'PBBS'):
            if usergrain:
                return False, ''
        if sched == 'PBBS':
            if fine:
                return False, ''
            if lowering in [CilkLowering.LazyD2, CilkLowering.LazyD0, CilkLowering.Nopoll]:
                return False, ''
        if lowering == CilkLowering.CilkPlus:
            if sched == 'DELEGATEPRC' or sched == 'DELEGATEPRCPRL':
                return False, ''
    suffix = f"{scheduler2suffix[sched]}{usergrain2suffix[usergrain]}{fine2suffix[fine]}{lowering2suffix[lowering]}"
    return True, suffix

def compile_benchmark_cilk5(suffix, task_scheduler, noopt, finergrainsize, cilk_lowering, benchmark_obj, output_dir):
    name = benchmark_obj.benchmark_name+'_'+benchmark_obj.name
    dump_string("Compiling " + name, 0, verbose)

    compiler_file_path = f"{output_dir}/{name}_compiler.txt"
    compile_cmd = f"./compile-cilk.sh {suffix} {benchmark_obj.name}"

    return runcmd(compile_cmd, compilation_timeout, compile_error_handler);

# if exe already exists, leave it, otherwise compile
# if options don't make sense, return success since we will never run it anyway
def compile_benchmark_pbbs_v2(suffix, task_scheduler, noopt, finergrainsize, cilk_lowering, benchmark_obj, output_dir):
    # executable path and name
    destdir = f"{benchmark_obj.benchmark_name}/{benchmark_obj.name}"
    exename = f"{destdir}/{benchmark_obj.binary}.{suffix}"

    # see if option we need it already there?
    if os.path.exists(exename):
        return CmdStatus.CORRECT, "", "Exists", ""

    goto_dir = f"cd {destdir}"

    dump_string(f"Compiling {benchmark_obj.name.replace('/', '_')}", 0, verbose)

    compile_cmd = [goto_dir, "&& make clean &&"]

    # set the schedule option if not PBBS
    if task_scheduler != "PBBS":
        compile_cmd.append(f"{task_scheduler}=1")

    # set grainsize options
    if noopt == 1:
        compile_cmd.append("NOOPT=1")
    if finergrainsize == 1:
        compile_cmd.append("GRAINSIZE8=1")

    # set lowering option
    if(cilk_lowering == CilkLowering.Serial):
        compile_cmd.append("SEQUENTIAL=1")
    elif (cilk_lowering == CilkLowering.LazyD2):
        compile_cmd.append("POLL2=1")
    elif (cilk_lowering == CilkLowering.Nopoll):
        compile_cmd.append("NOPOLL=1")
    elif (cilk_lowering == CilkLowering.SIGUSR):
        compile_cmd.append("TAPIR=1 GCILK11=1 SIGUSR=1")
    elif (cilk_lowering == CilkLowering.UIPI):
        compile_cmd.append("UIPI=1")
    elif (cilk_lowering == CilkLowering.LazyD0):
        compile_cmd.append("POLL0=1")
    elif (cilk_lowering == CilkLowering.CilkPlus):
        compile_cmd.append("OPENCILK=1")
    else:
        assert(0);

    # finally add 'make' and make into a string
    compile_cmd.append("make")
    compileString = " ".join(compile_cmd)

    compile_status, compiler_error, out, err = runcmd(compileString, compilation_timeout, compile_error_handler);
    if compile_status == CmdStatus.CORRECT:
        maybeRename(f"{destdir}/{benchmark_obj.binary}", exename)
    return compile_status, compiler_error, out, err

compileFunction = {
    "pbbs_v2": compile_benchmark_pbbs_v2,
    "cilk5": compile_benchmark_cilk5,
}

# Helper to compile benchmark. Returns 1 on success and 0 on error. Also returns
# simplified error string, which is "" if timeout or no error.
# if everything works, we only return LAST status, error, out, err
def compile_benchmark(options, benchmark_obj, output_dir):
    compile_status, compiler_error, out, err = CmdStatus.CORRECT, "never executed", "", ""
    for sched in options.task_scheduler:
        for noopt in options.noopt:
            for finergrainsize in options.finergrainsize:
                for cilk_lowering in options.cilk_lowering:
                    valid, suffix = makeExeSuffix(benchmark_obj.benchmark_name, sched, noopt, finergrainsize, cilk_lowering)
                    if not valid:
                        # print(f"COMP Skipping {benchmark_obj.benchmark_name}, {sched}, {noopt}, {finergrainsize}, {cilk_lowering}")
                        continue
                    else:
                        # print(f"COMP          {benchmark_obj.benchmark_name}, {sched}, {noopt}, {finergrainsize}, {cilk_lowering}")
                        pass
                    cfunc = compileFunction[benchmark_obj.benchmark_name]
                    compile_status, compiler_error, out, err = cfunc(suffix,
                                                                     sched,
                                                                     noopt,
                                                                     finergrainsize,
                                                                     cilk_lowering,
                                                                     benchmark_obj,
                                                                     output_dir)
                    if compile_status != CmdStatus.CORRECT:
                        return compile_status, compiler_error, out, err
                    showprogress(f"Compiled-{suffix}:")
    return compile_status, compiler_error, out, err

# Helper to create test file
def create_testfile(benchmark_obj, input_file):
    # test_cmd is the command to test the correctness of the benchmark.
    goto_dir =  "cd " + benchmark_obj.benchmark_name + "/" + benchmark_obj.name
    goto_dir_test = goto_dir + "/../" + benchmark_obj.data_dir + "/data/"
    test_cmd = goto_dir_test + " && pwd && make " + input_file

    return runcmd(test_cmd, check_benchmark_timout, run_error_handler);


# Get the load average over the last 1 minutes
def load_avg():
    load1, load5, load15 = os.getloadavg()
    return load1;

# Helper to run the benchmark. Returns run status of benchmark. If the run
# is successful, the execution time is returned. Otherwise, None is returned.
def run_benchmark(lazy_benchmark_options, suffix, benchmark_obj, num_cores, output_file, input_file):
    # Before executing the code, busy wait until /proc/loadavg is below than 1
    loadctr = 0;
    waitload = lazy_benchmark_options.wait_load
    while load_avg() > waitload:
        time.sleep(1)
        dump_string("Waiting for laod_avg to go below %d\n" % (waitload), 0, verbose)

    load1, load5, load15 = os.getloadavg()
    dump_string("Load average : the last 1 minutes: " + str(load1) + " the last 5 minutes: " + str(load5) + " the last 15 minutes: " + str(load15) + "\n", 0, verbose)

    if benchmark_obj.benchmark_name == "pbbs_v2":
        return run_benchmark_pbbs_v2(lazy_benchmark_options, suffix, benchmark_obj, num_cores, output_file, input_file);
    elif benchmark_obj.benchmark_name == "cilk5":
        return run_benchmark_cilk5(lazy_benchmark_options, suffix, benchmark_obj, num_cores, output_file, input_file);
    else:
        assert(0);

def run_benchmark_cilk5(lazy_benchmark_options, suffix, benchmark_obj, num_cores, output_file, input_file):
    # run_cmd is the commmand to run the benchmark.
    goto_dir =  "cd " + benchmark_obj.benchmark_name

    numa_cmd = "numactl --interleave=all"
    if(lazy_benchmark_options.disable_numa):
        numa_cmd = ""

    icache_cmd = ""
    if (lazy_benchmark_options.measure_icache):
        icache_cmd = "perf stat -x, -e icache.misses,icache.hit"

    binary = f"NAIVE_MAPPING=1 CILK_NWORKERS={num_cores} {numa_cmd} {icache_cmd}  ./{benchmark_obj.binary}.{suffix}"

    arguments = input_file + " " + str(lazy_benchmark_options.num_tests)
    run_cmd = goto_dir + " && " + binary + " " + arguments

    # Displays command being run from the perspective of the benchmark directory.
    res_time = []

    start_time = time.time()

    # The benchmark may have a bug causing an infinite loop. The process
    # is killed after a timeout time to move on to other tests.
    status, status_str, out, err = runcmd(run_cmd, check_benchmark_timout, run_error_handler);
    if(status == CmdStatus.INCORRECT):
        return CmdStatus.INCORRECT, None
    elif (status == CmdStatus.TIMEOUT):
        return CmdStatus.TIMEOUT, None

    pbbs_time_str = str(out)
    pbbs_time_str_arr = pbbs_time_str.split('\\n')
    pbbs_time_str_split = [s for s in pbbs_time_str_arr if "PBBS-time" in s];

    for pbbs_time_str_elem in pbbs_time_str_split:
        pbbs_time_str_elem_split = pbbs_time_str_elem.split(":")[1]
        res_time.append(float(pbbs_time_str_elem_split))

    end_time = time.time()
    dump_string(res_time, 0, verbose)

    return CmdStatus.CORRECT, res_time

def run_benchmark_pbbs_v2(lazy_benchmark_options, suffix, benchmark_obj, num_cores, output_file, input_file):
    # directory where we run benchmark
    gotodir = f"cd {benchmark_obj.benchmark_name}/{benchmark_obj.name}"

    # common options to all runs
    cmd = [gotodir,
           "&&",
           "NAIVE_MAPPING=1",
           f"CILK_NWORKERS={num_cores}",
           "LD_LIBRARY_PATH=../../../opencilk/cheetah/build/lib/x86_64-unknown-linux-gnu/",
           "" if lazy_benchmark_options.disable_numa else "numactl --interleave=all"
           ]

    # add icache perf if needed
    if lazy_benchmark_options.measure_icache:
        cmd.append("perf stat -x, -e icache.misses,icache.hit")

    # actually binary we are testing
    cmd.append(f"./{benchmark_obj.binary}.{suffix}")

    # add benchmark arguments
    cmd.extend(["-o", output_file, "-r", str(lazy_benchmark_options.num_tests), f"../{benchmark_obj.data_dir}/data/{input_file}"])
    cmdstr = " ".join(cmd)

    # Remove old output file and create new one.
    os.system(f"{gotodir} && touch {output_file}")
    res_time = []

    start_time = time.time()
    for iteration in range(n_iteration):
        # The benchmark may have a bug causing an infinite loop. The process
        # is killed after a timeout time to move on to other tests.
        status, status_str, out, err = runcmd(cmdstr, check_benchmark_timout, run_error_handler)
        if(status == CmdStatus.INCORRECT):
            return CmdStatus.INCORRECT, None
        elif (status == CmdStatus.TIMEOUT):
            return CmdStatus.TIMEOUT, None

        pbbs_time_str = str(out)
        pbbs_time_str_arr = pbbs_time_str.split('\\n')
        pbbs_time_str_split = [s for s in pbbs_time_str_arr if "Parlay time" in s];

        for pbbs_time_str_elem in pbbs_time_str_split:
            pbbs_time_str_elem_split = pbbs_time_str_elem.split(":")
            if("Parlay time" in pbbs_time_str_elem_split[0]):
                res_time.append(float(pbbs_time_str_elem_split[1]))

        if(lazy_benchmark_options.measure_icache):
            pbbs_icache_str = str(err.decode("utf-8"))
            pbbs_icache_str_arr = pbbs_icache_str.splitlines()
            pbbs_icache_str_split = [s for s in pbbs_icache_str_arr if "icache" in s];
            for pbbs_icache_str_elem in pbbs_icache_str_split:
                pbbs_icache_str_elem_split = pbbs_icache_str_elem.split(",")
                res_time.append(float(pbbs_icache_str_elem_split[0]))

        if(lazy_benchmark_options.measure_promotedtask):
            pbbs_icache_str = str(out)
            pbbs_icache_str_arr = pbbs_icache_str.split('\\n')
            pbbs_icache_str_split = [s for s in pbbs_icache_str_arr if "-1," in s];

            for pbbs_icache_str_elem in pbbs_icache_str_split:
                pbbs_icache_str_elem_split = pbbs_icache_str_elem.split(",")

                if("number of success push_workctx" in pbbs_icache_str_elem_split[1]):
                    res_time.append(float(pbbs_icache_str_elem_split[2]))
                elif("work size" in pbbs_icache_str_elem_split[1]):
                    res_time.append(float(pbbs_icache_str_elem_split[2]))
                elif("number of total tasks" in pbbs_icache_str_elem_split[1]):
                    res_time.append(float(pbbs_icache_str_elem_split[2]))


    end_time = time.time()
    dump_string(res_time, 0, verbose)
    return CmdStatus.CORRECT, res_time


# Helper to run the benchmark. Run status is returned.
def run_check_benchmark(lazy_benchmark_options, benchmark_obj, output_file, input_file):
    if benchmark_obj.benchmark_name == "pbbs_v2":
        return run_check_benchmark_pbbs_v2(lazy_benchmark_options, benchmark_obj, output_file, input_file);
    elif benchmark_obj.benchmark_name == "cilk5":
        return run_check_benchmark_cilk5(lazy_benchmark_options, benchmark_obj, output_file, input_file);
    else:
        assert(0);

def run_check_benchmark_cilk5(lazy_benchmark_options, benchmark_obj, output_file, input_file):
    # TODO: Do something with this
    return CmdStatus.CORRECT,  "", "", ""

def run_check_benchmark_pbbs_v2(lazy_benchmark_options, benchmark_obj, output_file, input_file):
    # test_cmd is the command to test the correctness of the benchmark.
    goto_dir =  "cd " + benchmark_obj.benchmark_name + "/" +  benchmark_obj.name
    goto_dir_test = goto_dir + "/../bench/"
    #binary_test = "CILK_NWORKERS=`nproc` ./" + benchmark_obj.check_binary
    binary_test = "CILK_NWORKERS=1 ./" + benchmark_obj.check_binary
    arguments_test = "../" + benchmark_obj.data_dir + "/data/" + input_file + " " + "../../" + benchmark_obj.name + "/" + output_file
    test_cmd = goto_dir_test + " && pwd && " + binary_test + " " + arguments_test

    return runcmd(test_cmd, check_benchmark_timout, run_error_handler)

# options are overall options
# iopt is the compiler options we are using for this run
def execute_benchmark(benchmark_obj, options, iopt, csv_writer, csv_file, test_cores, data_set):
    numTests = options.num_tests
    for num_cores in test_cores:
        row = [""] * (num_cols + numTests*n_iteration - 1)

        # Create a function for this
        if(options.measure_icache):
            row = [""] * (num_cols + (numTests+2)*n_iteration - 1)

        if(options.measure_promotedtask):
            row = [""] * (num_cols + (numTests+3)*n_iteration - 1)

        row[int(ColName.BENCHMARK)] = benchmark_obj.name + "/" + benchmark_obj.binary
        row[int(ColName.COMPILES)] = "Yes"
        row[int(ColName.DATASET)] = data_set
        row[int(ColName.NUM_CORES)] = num_cores
        row[int(ColName.DISABLE_NUMA)] = "No"
        if(options.disable_numa):
            row[int(ColName.DISABLE_NUMA)] = "Yes"
        row[int(ColName.PARALLEL_FRAMEWORK)] = iopt.get_cilklowering_str()
        row[int(ColName.TASK_SCHEDULER)] = iopt.task_scheduler
        row[int(ColName.PFORMAXGRAINSIZE)] = 2048
        if(iopt.finergrainsize == 1):
            row[int(ColName.PFORMAXGRAINSIZE)] = 8
        row[int(ColName.IGNORE_USER_PFORGAINSIZE)] = "No"
        if(iopt.noopt == 1):
            row[int(ColName.IGNORE_USER_PFORGAINSIZE)] = "Yes"

        dump_string("Running benchmark: %s dataset: %s, num_cores: %s\n" % (benchmark_obj.binary, data_set, num_cores),
                    0,
                    verbose)

        # Make sure paths adjusted when executing commands
        output_file = data_set + "_" + str(num_cores) + "cores_out_file"
        start_row = int(ColName.TIME)

        # Run the benchmark
        run_status, run_time = run_benchmark(options, iopt.extension, benchmark_obj, num_cores, output_file, data_set)
        row[int(ColName.STATUS)] = get_run_status_str(run_status)
        if run_status == CmdStatus.CORRECT:
            check_status, message, out, err = run_check_benchmark(options, benchmark_obj, output_file, data_set)
            if check_status == CmdStatus.CORRECT:
                for res in run_time:
                    row[start_row] = res;
                    start_row = start_row + 1
            else:
                for res in run_time:
                    row[start_row] = 'N/A'
                    start_row = start_row + 1
                row[int(ColName.STATUS)] = get_run_status_str(CmdStatus.INCORRECT)
                row[int(ColName.ERROR_MSG)] = "Verification failed"
                run_status = CmdStatus.INCORRECT
        else:
            for res in range(0, numTests):
                row[start_row] = 'N/A'
                start_row = start_row + 1

            #row[start_row] = "N/A"
            row[int(ColName.STATUS)] = get_run_status_str(CmdStatus.INCORRECT)
            row[int(ColName.ERROR_MSG)] = "Benchmark failed to run"
            run_status = CmdStatus.INCORRECT

        csv_writer.writerow(row)

    written_row = start_row
    return written_row

def execute_benchmark_top(benchmark_obj, options, csv_writer, csv_file, test_cores, compile_status, compiler_error):
    # generate list of executable suffixes to run
    suffixes = []
    for sched in options.task_scheduler:
        for noopt in options.noopt:
            for finergrainsize in options.finergrainsize:
                for cilk_lowering in options.cilk_lowering:
                    valid, suffix = makeExeSuffix(benchmark_obj.benchmark_name, sched, noopt, finergrainsize, cilk_lowering)
                    if valid:
                        suffixes.append(CompilerOptions(sched, noopt, finergrainsize, cilk_lowering, suffix))
                    else:
                        # print(f"EXEC Skipping {benchmark_obj.benchmark_name}, {sched}, {noopt}, {finergrainsize}, {cilk_lowering}")
                        pass


    # Go through the benchmark's data sets.
    inputs = benchmark_obj.standard_inputs
    for data_set in inputs:
        # Used to determine when data set name should be written to csv file.
        # Path from benchmark directory.
        data_path = f"{benchmark_obj.benchmark_name}/{benchmark_obj.name}/../{benchmark_obj.data_dir}/data/{data_set}"
        if not os.path.isfile(data_path) and (benchmark_obj.benchmark_name == "pbbs_v2") :
            dump_string("No data set: " + data_set + " Creating test file", 0, verbose)

            create_status, message, out, err =  create_testfile(benchmark_obj, data_set)
            if create_status != CmdStatus.CORRECT:
                logging.warning("Failed to create test")
                continue
            showprogress(f"data:{data_set}")

        # for each different executable option
        for suffix in suffixes:
            # Run the benchmark for a different number of cores.
            execute_benchmark(benchmark_obj, options, suffix, csv_writer, csv_file, test_cores, data_set);
            showprogress(f",ran:{suffix.extension}")
    showprogress("\n")

def main():

    # Get the bencjmark to run
    benchmarks_to_run = parse_csv(input_file)

    output_dir = "oDir/lazybenchmark_output_files_" + time.strftime("%Y%m%d-%H%M%S")
    results_file = "lazybenchmark_results.csv"

    print(f"Will put results and log files in {output_dir}")
    lazy_benchmark_options = LazyBenchmarkOptions(compile_only, execute_only, num_cores, num_tests, benchmarks_to_run, cilk_lowering, task_scheduler, noopt, finergrainsize, measure_icache, False, disable_numa, verbose, dry_run, wait_load);


    # Number of cores for which benchmarks should be tested.
    test_cores = get_test_num_cores(lazy_benchmark_options.num_cores)

    # Write output
    os.mkdir(output_dir)
    csv_file = open(output_dir + "/" + results_file, "a", newline="")
    csv_writer = csv.writer(csv_file)

    # Setup logger
    logging.basicConfig(filename=output_dir+ "/" + 'log.txt', level=logging.DEBUG, format='')

    # Write category names on first row.

    #for i in range(0, lazy_benchmark_options.num_tests-1):
    #    results_file_categories.append(f"Time {i}")

    #results_file_categories.append("Error Message")
    #ERROR_MSG = len(results_file_categories)-1

    # If icache experiment is enabled, append the last two column with icache misses and icache hits
    #if (lazy_benchmark_options.measure_icache):
    #    results_file_categories.append("Icache Misses")
    #    results_file_categories.append("Icache Hits")

    csv_writer.writerow(results_file_categories)

    if test_cores == []:
        return

    for i in range(len(lazy_benchmark_options.benchmarks_to_run)):
        if (i != (len(lazy_benchmark_options.benchmarks_to_run) - 1)):
            dump_string("%s, " % lazy_benchmark_options.benchmarks_to_run[i].name, 0, lazy_benchmark_options.verbose)
        else:
            dump_string("%s\n\n" % lazy_benchmark_options.benchmarks_to_run[i].name, 0, lazy_benchmark_options.verbose)

    # Loop through the benchmarks
    for benchmark_obj in lazy_benchmark_options.benchmarks_to_run:
        # Used to determine when benchmark name / compile status should be written
        # to csv file.
        benchmark_path_name = benchmark_obj.benchmark_name + "/" + benchmark_obj.name
        showprogress(f"{benchmark_path_name}:")

        dump_string("\nTest " + benchmark_path_name + ":\n", 0, lazy_benchmark_options.verbose)
        dump_string("Settting up test:",  0, lazy_benchmark_options.verbose)

        # compile benchmark
        if(not lazy_benchmark_options.execute_only):
            compile_status, compiler_error, out, err = compile_benchmark(lazy_benchmark_options, benchmark_obj, output_dir)
        else:
            compile_status = CmdStatus.CORRECT;
            compiler_error = "testPBBS run without compiling benchmark"
            showprogress(f"Compiled-Skipped:")

        if (compile_status != CmdStatus.CORRECT) or lazy_benchmark_options.compile_only:
            # Create  a function for this
            row = [""] * num_cols
            row[int(ColName.BENCHMARK)] = benchmark_obj.name + "/" + benchmark_obj.binary
            if compile_status == CmdStatus.CORRECT:
                row[int(ColName.COMPILES)] = "Yes"
            else:
                row[int(ColName.COMPILES)] = "No"
            row[int(ColName.ERROR_MSG)] = compiler_error
            row[int(ColName.PARALLEL_FRAMEWORK)] = lazy_benchmark_options.get_cilklowering_str()
            row[int(ColName.TASK_SCHEDULER)] = lazy_benchmark_options.task_scheduler
            row[int(ColName.PFORMAXGRAINSIZE)] = 2048
            if(lazy_benchmark_options.finergrainsize == 1):
                row[int(ColName.PFORMAXGRAINSIZE)] = 8
            row[int(ColName.IGNORE_USER_PFORGAINSIZE)] = "No"
            if(lazy_benchmark_options.noopt == 1):
                row[int(ColName.IGNORE_USER_PFORGAINSIZE)] = "Yes"

            csv_writer.writerow(row)
            continue

        # execute benchmark
        execute_benchmark_top(benchmark_obj, lazy_benchmark_options, csv_writer, csv_file, test_cores, compile_status, compiler_error)


    csv_file.close()

# Main entry
main()
