#!/usr/bin/env bash

NUM_CORES=$1
NUM_TESTS=$2
DISABLE_NUMA=$3


if [ ${DISABLE_NUMA} -eq 1 ]; then
    ./testBenchmark_compile.py --num_cores=${NUM_CORES} --num_tests=${NUM_TESTS} --parallel_framework lazyd0 tapir --schedule_tasks DELEGATEPRCPRL OPENCILKDEFAULT_FINE PBBS --fg both --noopt no --disable_numa
else
    ./testBenchmark_compile.py --num_cores=${NUM_CORES} --num_tests=${NUM_TESTS} --parallel_framework lazyd0 tapir --schedule_tasks DELEGATEPRCPRL OPENCILKDEFAULT_FINE PBBS --fg both --noopt no 
fi
