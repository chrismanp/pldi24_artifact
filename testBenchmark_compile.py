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

class ColName(IntEnum):
    BENCHMARK = 0;
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
class CmdStatus(Enum):
    CORRECT = 1
    INCORRECT = 2
    TIMEOUT = 3

class CilkLowering(Enum):
    Serial = 0;
    LazyD2 = 1
    Nopoll = 2
    SIGUSR = 3
    UIPI = 4
    LazyD0 = 5
    CilkPlus = 6

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

# Gets string representation of run status.
def get_run_status_str(run_status):
    if run_status == CmdStatus.CORRECT:
        return "Correct"
    elif run_status == CmdStatus.INCORRECT:
        return "Incorrect"
    else:
        return "Timeout"

def get_cilklowering_str(cilk_lowering) :
    if(cilk_lowering == CilkLowering.Serial):
        return "Serial"
    elif (cilk_lowering == CilkLowering.LazyD2):
        return "LazyD with Frequent Polling"
    elif (cilk_lowering == CilkLowering.Nopoll):
        return "LazyD with No Polling"
    elif (cilk_lowering == CilkLowering.LazyD0):
        return "LazyD with InFrequent Polling"
    elif (cilk_lowering == CilkLowering.CilkPlus):
        return "OpenCilk"
    else:
        assert(0);

def dump_string(str, w, v):
    if w:
        logging.warning(str)
    else:
        logging.debug(str)
    if(v):
        print(str)

# Run a command
# Return status and message
def runcmd(cmd, timeout, error_handler, lazy_benchmark_options):
    if lazy_benchmark_options.dry_run:
        dump_string("Command: " + cmd, 0, 1)
        return CmdStatus.CORRECT, "", "", ""
    else:
        dump_string("Command: " + cmd, 0, lazy_benchmark_options.verbose)

    p_process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    try:
        out, err = p_process.communicate(timeout)
        out = str(out)
        err = str(err)
        dump_string(out, 0, lazy_benchmark_options.verbose)
        dump_string(err, 1, lazy_benchmark_options.verbose)
        status, error_string = error_handler(p_process, out, err)
        return status, error_string, out, err
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

# Helper to compile benchmark. Returns 1 on success and 0 on error. Also returns
# simplified error string, which is "" if timeout or no error.
def compile_benchmark(lazy_benchmark_options, benchmark_obj, output_dir):
    if benchmark_obj.benchmark_name == "pbbs_v2":
        return compile_benchmark_pbbs_v2(lazy_benchmark_options, benchmark_obj, output_dir)
    elif benchmark_obj.benchmark_name == "cilk5":
        return compile_benchmark_cilk5(lazy_benchmark_options, benchmark_obj, output_dir)
    else:
        assert(0)

def compile_benchmark_cilk5(lazy_benchmark_options, benchmark_obj, output_dir):
    name = benchmark_obj.benchmark_name+'_'+benchmark_obj.name
    dump_string("Compiling " + name, 0, lazy_benchmark_options.verbose)

    compiler_file_path = output_dir + "/" + name + "_compiler.txt"
    compile_cmd = ""

    if(lazy_benchmark_options.cilk_lowering == CilkLowering.Serial):
        compile_cmd = " bash ./testCilk.sh -s -x=0 -w=0 " + benchmark_obj.name
    elif (lazy_benchmark_options.cilk_lowering == CilkLowering.LazyD2):
        compile_cmd = " bash ./testCilk.sh -lf -x=0 -w=0 " + benchmark_obj.name
    elif (lazy_benchmark_options.cilk_lowering == CilkLowering.Nopoll):
        compile_cmd = " bash ./testCilk.sh -ef -x=0 -w=0 " + benchmark_obj.name
    elif (lazy_benchmark_options.cilk_lowering == CilkLowering.SIGUSR):
        compile_cmd = " bash ./testCilk.sh -sf -x=0 -w=0 " + benchmark_obj.name
    elif (lazy_benchmark_options.cilk_lowering == CilkLowering.UIPI):
        compile_cmd = " bash ./testCilk.sh -uif -x=0 -w=0 " + benchmark_obj.name
    elif (lazy_benchmark_options.cilk_lowering == CilkLowering.LazyD0):
        compile_cmd = " bash ./testCilk.sh -uf -x=0 -w=0 " + benchmark_obj.name
    elif (lazy_benchmark_options.cilk_lowering == CilkLowering.CilkPlus):
        compile_cmd = " bash ./testCilk.sh -t -x=0 -w=0 " + benchmark_obj.name
    else:
        assert(0);

    # Create a function wrapper for this
    #dump_string("Compile command" + compile_cmd, lazy_benchmark_options.verbose)

    return runcmd(compile_cmd, compilation_timeout, compile_error_handler, lazy_benchmark_options);

def compile_benchmark_pbbs_v2(lazy_benchmark_options, benchmark_obj, output_dir):
    # Remove old files and compile the benchmark.
    goto_dir = "cd " + benchmark_obj.benchmark_name + "/" + benchmark_obj.name

    name = '_'.join(s for s in benchmark_obj.name.split("/"))
    dump_string("Compiling " + name, 0, lazy_benchmark_options.verbose)

    compiler_file_path = output_dir + "/" + name + "_compiler.txt"
    compile_cmd = ""

    additional_options = ""

    if( lazy_benchmark_options.task_scheduler == "PRC"):
        additional_options += "PRC=1"
    elif( lazy_benchmark_options.task_scheduler == "PRL"):
        additional_options += "PRL=1"
    elif( lazy_benchmark_options.task_scheduler == "PRCPRL"):
        additional_options += "PRCPRL=1"
    elif( lazy_benchmark_options.task_scheduler == "DELEGATEPRC"):
        additional_options += "DELEGATEPRC=1"
    elif( lazy_benchmark_options.task_scheduler == "DELEGATEPRCPRL"):
        additional_options += "DELEGATEPRCPRL=1"
    elif( lazy_benchmark_options.task_scheduler == "OPENCILKDEFAULT_FINE"):
        additional_options += "OPENCILKDEFAULT_FINE=1"

    if(lazy_benchmark_options.noopt == 1):
        additional_options += " NOOPT=1"

    if(lazy_benchmark_options.finergrainsize == 1):
        additional_options += " GRAINSIZE8=1"


    if(lazy_benchmark_options.cilk_lowering == CilkLowering.Serial):
        compile_cmd = goto_dir + " && make clean && SEQUENTIAL=1 make"
    elif (lazy_benchmark_options.cilk_lowering == CilkLowering.LazyD2):
        compile_cmd = goto_dir + " && make clean && " + additional_options + " POLL2=1 make "
    elif (lazy_benchmark_options.cilk_lowering == CilkLowering.Nopoll):
        compile_cmd = goto_dir + " && make clean && " + additional_options + " NOPOLL=1 make "
    elif (lazy_benchmark_options.cilk_lowering == CilkLowering.SIGUSR):
        compile_cmd = goto_dir + " && make clean && TAPIR=1 GCILK11=1 make SIGUSR=1 "
    elif (lazy_benchmark_options.cilk_lowering == CilkLowering.UIPI):
        compile_cmd = goto_dir + " && make clean && UIPI=1 make "
    elif (lazy_benchmark_options.cilk_lowering == CilkLowering.LazyD0):
        compile_cmd = goto_dir + " && make clean && " + additional_options + " POLL0=1 make "
    elif (lazy_benchmark_options.cilk_lowering == CilkLowering.CilkPlus):
        compile_cmd = goto_dir + " && make clean && " + additional_options + " OPENCILK=1 make "
    else:
        assert(0);

    return runcmd(compile_cmd, compilation_timeout, compile_error_handler, lazy_benchmark_options);

# Helper to create test file
def create_testfile(benchmark_obj, input_file, lazy_benchmark_options):
    # test_cmd is the command to test the correctness of the benchmark.
    goto_dir =  "cd " + benchmark_obj.benchmark_name + "/" + benchmark_obj.name
    goto_dir_test = goto_dir + "/../" + benchmark_obj.data_dir + "/data/"
    test_cmd = goto_dir_test + " && pwd && make " + input_file

    return runcmd(test_cmd, check_benchmark_timout, run_error_handler, lazy_benchmark_options);


# Get the load average over the last 1 minutes
def load_avg():
    load1, load5, load15 = os.getloadavg()
    return load1;

# Helper to run the benchmark. Returns run status of benchmark. If the run
# is successful, the execution time is returned. Otherwise, None is returned.
def run_benchmark(lazy_benchmark_options, benchmark_obj, num_cores, output_file, input_file):
    # Before executing the code, busy wait until /proc/loadavg is below than 1
    loadctr = 0;
    waitload = lazy_benchmark_options.wait_load
    while load_avg() > waitload:
        loadctr = loadctr+1;
        if(loadctr == 1000000):
            dump_string("Waiting for laod_avg to go below %d\n" % (waitload), 0, lazy_benchmark_options.verbose)
            loadctr=0;
        continue

    load1, load5, load15 = os.getloadavg()
    dump_string("Load average : the last 1 minutes: " + str(load1) + " the last 5 minutes: " + str(load5) + " the last 15 minutes: " + str(load15) + "\n", 0, lazy_benchmark_options.verbose)


    if benchmark_obj.benchmark_name == "pbbs_v2":
        return run_benchmark_pbbs_v2(lazy_benchmark_options, benchmark_obj, num_cores, output_file, input_file);
    elif benchmark_obj.benchmark_name == "cilk5":
        return run_benchmark_cilk5(lazy_benchmark_options, benchmark_obj, num_cores, output_file, input_file);
    else:
        assert(0);

def run_benchmark_cilk5(lazy_benchmark_options, benchmark_obj, num_cores, output_file, input_file):
    # run_cmd is the commmand to run the benchmark.
    goto_dir =  "cd " + benchmark_obj.benchmark_name

    numa_cmd = "numactl --interleave=all"
    if(lazy_benchmark_options.disable_numa):
        numa_cmd = ""

    binary = "NAIVE_MAPPING=1 CILK_NWORKERS=" + str(num_cores) + " " + numa_cmd + "  ./" + benchmark_obj.binary

    arguments = input_file + " " + str(lazy_benchmark_options.num_tests)
    run_cmd = goto_dir + " && " + binary + " " + arguments

    # Displays command being run from the perspective of the benchmark directory.
    res_time = []

    start_time = time.time()

    # The benchmark may have a bug causing an infinite loop. The process
    # is killed after a timeout time to move on to other tests.
    status, status_str, out, err = runcmd(run_cmd, check_benchmark_timout, run_error_handler, lazy_benchmark_options);
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
    dump_string(res_time, 0, lazy_benchmark_options.verbose)

    return CmdStatus.CORRECT, res_time

def run_benchmark_pbbs_v2(lazy_benchmark_options, benchmark_obj, num_cores, output_file, input_file):
    # run_cmd is the commmand to run the benchmark.
    goto_dir =  "cd " + benchmark_obj.benchmark_name + "/" + benchmark_obj.name

    numa_cmd = "numactl --interleave=all"
    if(lazy_benchmark_options.disable_numa):
        numa_cmd = ""

    binary = "NAIVE_MAPPING=1 " + " CILK_NWORKERS=" + str(num_cores) + " LD_LIBRARY_PATH=../../../opencilk/cheetah/build/lib/x86_64-unknown-linux-gnu/ "+ numa_cmd + "  ./" + benchmark_obj.binary

    if(lazy_benchmark_options.measure_icache):
        binary = "NAIVE_MAPPING=1 " + " CILK_NWORKERS=" + str(num_cores) + " LD_LIBRARY_PATH=../../../opencilk/cheetah/build/lib/x86_64-unknown-linux-gnu/ numactl --interleave=all perf stat -x, -e icache.misses,icache.hit -a ./" + benchmark_obj.binary


    arguments = "-o " + output_file + " -r " + str(lazy_benchmark_options.num_tests) + " " + "../" + benchmark_obj.data_dir + "/data/" + input_file
    run_cmd = goto_dir + " && " + binary + " " + arguments

    # Remove old output file and create new one.
    os.system(goto_dir + " && touch " + output_file)
    res_time = []

    # TODO: FIX this, get the performance number from the actual code
    start_time = time.time()


    for iteration in range(n_iteration):
        # The benchmark may have a bug causing an infinite loop. The process
        # is killed after a timeout time to move on to other tests.


        status, status_str, out, err = runcmd(run_cmd, check_benchmark_timout, run_error_handler, lazy_benchmark_options);
        if(status == CmdStatus.INCORRECT):
            return CmdStatus.INCORRECT, None
        elif (status == CmdStatus.TIMEOUT):
            return CmdStatus.TIMEOUT, None

        pbbs_time_str = str(out)
        pbbs_time_str_arr = pbbs_time_str.split('\\n')
        pbbs_time_str_split = [s for s in pbbs_time_str_arr if "Parlay time" in s];

        for pbbs_time_str_elem in pbbs_time_str_split:
            pbbs_time_str_elem_split = pbbs_time_str_elem.split(":")
            #logging.warning(pbbs_time_str_elem_split)
            if("Parlay time" in pbbs_time_str_elem_split[0]):
                res_time.append(float(pbbs_time_str_elem_split[1]))

        if(lazy_benchmark_options.measure_icache):
            pbbs_icache_str = str(out)
            pbbs_icache_str_arr = pbbs_icache_str.split('\\n')
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
    dump_string(res_time, 0, lazy_benchmark_options.verbose)
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

    return runcmd(test_cmd, check_benchmark_timout, run_error_handler, lazy_benchmark_options);

def execute_benchmark(benchmark_obj, lazy_benchmark_options, csv_writer, csv_file, test_cores, data_set):
    for num_cores in test_cores:
        row = [""] * (num_cols + lazy_benchmark_options.num_tests*n_iteration - 1)

        # Create a function for this
        if(lazy_benchmark_options.measure_icache):
            row = [""] * (num_cols + (lazy_benchmark_options.num_tests+2)*n_iteration - 1)

        if(lazy_benchmark_options.measure_promotedtask):
            row = [""] * (num_cols + (lazy_benchmark_options.num_tests+3)*n_iteration - 1)

        row[int(ColName.BENCHMARK)] = benchmark_obj.name + "/" + benchmark_obj.binary
        row[int(ColName.COMPILES)] = "Yes"
        row[int(ColName.DATASET)] = data_set
        row[int(ColName.NUM_CORES)] = num_cores
        row[int(ColName.DISABLE_NUMA)] = "No"
        if(lazy_benchmark_options.disable_numa):
            row[int(ColName.DISABLE_NUMA)] = "Yes"
        row[int(ColName.PARALLEL_FRAMEWORK)] = get_cilklowering_str(lazy_benchmark_options.cilk_lowering)
        row[int(ColName.TASK_SCHEDULER)] = lazy_benchmark_options.task_scheduler
        row[int(ColName.PFORMAXGRAINSIZE)] = 2048
        if(lazy_benchmark_options.finergrainsize == 1):
            row[int(ColName.PFORMAXGRAINSIZE)] = 8
        row[int(ColName.IGNORE_USER_PFORGAINSIZE)] = "No"
        if(lazy_benchmark_options.noopt == 1):
            row[int(ColName.IGNORE_USER_PFORGAINSIZE)] = "Yes"

        dump_string("Running benchmark: %s dataset: %s, num_cores: %s\n" % (benchmark_obj.binary, data_set, num_cores), 0, lazy_benchmark_options.verbose)

        # Make sure paths adjusted when executing commands
        output_file = data_set + "_" + str(num_cores) + "cores_out_file"
        start_row = int(ColName.TIME)

        # Run the benchmark
        run_status, run_time = run_benchmark(lazy_benchmark_options, benchmark_obj, num_cores, output_file, data_set)
        row[int(ColName.STATUS)] = get_run_status_str(run_status)
        if run_status == CmdStatus.CORRECT:
            check_status, message, out, err = run_check_benchmark(lazy_benchmark_options, benchmark_obj, output_file, data_set)
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
            for res in range(0, lazy_benchmark_options.num_tests):
                row[start_row] = 'N/A'
                start_row = start_row + 1

            #row[start_row] = "N/A"
            row[int(ColName.STATUS)] = get_run_status_str(CmdStatus.INCORRECT)
            row[int(ColName.ERROR_MSG)] = "Benchmark failed to run"
            run_status = CmdStatus.INCORRECT
            break

        csv_writer.writerow(row)

    written_row = start_row
    return written_row

def execute_benchmark_top(benchmark_obj, lazy_benchmark_options, csv_writer, csv_file, test_cores, compile_status, compiler_error):
    written_row = ColName.TIME
    # Go through the benchmark's data sets.
    inputs = benchmark_obj.standard_inputs
    for data_set in inputs:
        # Used to determine when data set name should be written to csv file.
        # Path from benchmark directory.
        data_path = benchmark_obj.benchmark_name + "/" + benchmark_obj.name + "/../" + benchmark_obj.data_dir + "/data/" + data_set
        if not os.path.isfile(data_path) and (benchmark_obj.benchmark_name == "pbbs_v2") :
            dump_string("No data set: " + data_set + " Creating test file", 0, lazy_benchmark_options.verbose)

            create_status, message, out, err =  create_testfile(benchmark_obj, data_set, lazy_benchmark_options)
            if create_status != CmdStatus.CORRECT:
                logging.warning("Failed to create test")
                continue

        # Run the benchmark for a different number of cores.
        written_row = execute_benchmark(benchmark_obj, lazy_benchmark_options, csv_writer, csv_file, test_cores, data_set);

    # Is this even needed?
"""
    if written_row == int(ColName.TIME):
        row = [""] * (num_cols + lazy_benchmark_options.num_tests-1)

        if(lazy_benchmark_options.measure_icache):
            row = [""] * (num_cols + (lazy_benchmark_options.num_tests+2) - 1)

        if(lazy_benchmark_options.measure_promotedtask):
            row = [""] * (num_cols + (lazy_benchmark_options.num_tests+3) - 1)

        row[int(ColName.BENCHMARK)] = benchmark_obj.name + "/" + benchmark_obj.binary
        if compile_status:
            row[int(ColName.COMPILES)] = "Yes"
        else:
            row[int(ColName.COMPILES)] = "No"
        row[written_row+1] = compiler_error
        csv_writer.writerow(row)
"""



def main():
    # Pargse the argument
    # setup arguments
    parser = argparse.ArgumentParser(description='Option to ')
    parser.add_argument("--compile", action='store_true', help="Only compile benchmark")
    parser.add_argument("--num_cores", nargs='+', default=['1'], help="Number of cores used. Can be a list of number of cores")
    parser.add_argument("--num_tests", default=1, type=int, help="Number of runs")
    parser.add_argument("--execute", action='store_true', help="Only execute benchmark")
    parser.add_argument("--disable_numa", action='store_true', help="Disable numa when running the benchmark")
    parser.add_argument("--icache", action='store_true', help="Run the icache experiment")
    parser.add_argument("--parallel_framework", default='tapir', choices=['lazyd0', 'lazyd2', 'nopoll', 'serial', 'tapir'], help="What parallel framework to use (options: lazyd0, lazyd2, nopoll, serial, tapir). Default tapir")
    parser.add_argument("--fg", action='store_true', help="Use finer grainsize. Only for LazyD and OpenCilk-fg")
    parser.add_argument("--noopt", action='store_true', help="Ignore users grainsize")
    parser.add_argument("--schedule_tasks", default="PBBS", choices=['PRC', 'PRL', 'DELEGATEPRC', 'PRCPRL', 'DELEGATEPRCPRL', 'OPENCILKDEFAULT_FINE', 'PBBS'], help="How to scheduler parallel task in pfor. Options: PRC, PRL, DELPRC, PRCPRL, DELPRCPRL, OPENCILKDEFAULT_FINE, PBBS")
    parser.add_argument("--ifile", default="lazybenchmark.csv", help="Input file")
    parser.add_argument("-v", "--verbose", action='store_true', help="Verbose")
    parser.add_argument("--dry_run", action='store_true', help="Dry run")
    parser.add_argument("--wait_load", default=10, type=int, help="The minimum load to execute the benchmark (Default=10)")

    # parse arguments
    flags = parser.parse_args()
    compile_only = flags.compile
    execute_only = flags.execute
    num_cores = flags.num_cores
    num_tests = flags.num_tests
    disable_numa = flags.disable_numa
    wait_load = flags.wait_load
    finergrainsize = flags.fg
    measure_icache = flags.icache
    noopt = flags.noopt
    input_file = flags.ifile
    parallel_framework = flags.parallel_framework
    task_scheduler = flags.schedule_tasks
    verbose = flags.verbose
    dry_run = flags.dry_run
    cilk_lowering = CilkLowering.LazyD0
    if (parallel_framework == "lazyd2"):
        cilk_lowering = CilkLowering.LazyD2
    elif (parallel_framework == "lazyd0"):
        cilk_lowering = CilkLowering.LazyD0
    elif (parallel_framework == "nopoll"):
        cilk_lowering = CilkLowering.Nopoll
    elif (parallel_framework == "tapir"):
        cilk_lowering = CilkLowering.CilkPlus
    elif (parallel_framework == "serial"):
        cilk_lowering = CilkLowering.Serial

    # Get the bencjmark to run
    benchmarks_to_run = parse_csv(input_file)

    output_dir = "oDir/lazybenchmark_output_files_" + time.strftime("%Y%m%d-%H%M%S")
    results_file = "lazybenchmark_results.csv"

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

        dump_string("\nTest " + benchmark_path_name + ":\n", 0, lazy_benchmark_options.verbose)
        dump_string("Settting up test:",  0, lazy_benchmark_options.verbose)

        # compile benchmark
        if(not lazy_benchmark_options.execute_only):
            compile_status, compiler_error, out, err = compile_benchmark(lazy_benchmark_options, benchmark_obj, output_dir)
        else:
            compile_status = CmdStatus.CORRECT;
            compiler_error = "testPBBS run without compiling benchmark"

        if (compile_status != CmdStatus.CORRECT) or lazy_benchmark_options.compile_only:
            # Create  a function for this
            row = [""] * num_cols
            row[int(ColName.BENCHMARK)] = benchmark_obj.name + "/" + benchmark_obj.binary
            if compile_status == CmdStatus.CORRECT:
                row[int(ColName.COMPILES)] = "Yes"
            else:
                row[int(ColName.COMPILES)] = "No"
            row[int(ColName.ERROR_MSG)] = compiler_error
            row[int(ColName.PARALLEL_FRAMEWORK)] = get_cilklowering_str(lazy_benchmark_options.cilk_lowering)
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
