#!/usr/bin/env python3
"""
Test script to convert csv file into latex table
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
import statistics
from scipy.stats import gmean
from enum import Enum
from enum import IntEnum

class ColName(IntEnum):
    BENCHMARK = 0;
    COMPILES = 1
    DATASET = 2
    NUM_CORES = 3
    STATUS = 4
    DISABLE_NUMA = 5
    PARALLEL_FRAMEWORK = 6
    TASK_SCHEDULER=7
    PFOR_MAXGRAINSIZE=8
    IGNORE_USERS_PFORGRAINSIZE=9
    TIME=10
    ERROR_MSG=11

fp_format = '.2f'

# Represent the row of the csv file
binaryname2implname = {        
        "LazyD with Frequent Polling+DELEGATEPRCPRL+8+cg" : "LazyD",
        "LazyD with InFrequent Polling+DELEGATEPRCPRL+8+cg" : "LazyD",
        "LazyD with InFrequent Polling+PRCPRL+8+cg" : "LazyD-EF",
        "LazyD with Frequent Polling+PRCPRL+8+cg" : "LazyD-EF",
        "LazyD with InFrequent Polling+DELEGATEPRC+8+cg" : "LazyD-PRL",
        "LazyD with Frequent Polling+DELEGATEPRC+8+cg" : "LazyD-PRL",
        "OpenCilk+OPENCILKDEFAULT_FINE+8+cg" : "OpenCilk.fine",
        "LazyD with Frequent Polling+DELEGATEPRCPRL+8+nocg" : "LazyD-cg",
        "LazyD with InFrequent Polling+DELEGATEPRCPRL+8+nocg" : "LazyD-cg",
        "OpenCilk+PBBS+2048+nocg" : "OpenCilk-cg",
        "OpenCilk+PBBS+2048+cg" : "OpenCilk",
        "LazyD with No Polling+PRL+8+cg" : "LazyD-poll",
        "Serial" : "Serial"
    }

def checkValid(opt):
    if opt not in binaryname2implname:
        return -1
        
def getImplNameArg(opt):
    if (checkValid(opt) != -1):
        return binaryname2implname[opt]
    else:
        return opt

def ignore_impl (impl, baseline_impl_name, tex):
    if (impl == baseline_impl_name) or (tex and '+' in impl):
        return 1

def calculate_mr (imisses, ihits):
    if imisses < 0:
        return -1
    return 100* imisses/(imisses + ihits)

# Generate the table
def process_results(set_of_impl, list_of_results, samples, tex, icache):
    set_of_impl = sorted(set_of_impl)

    perc = '%'
    if(tex):
        perc = '\%'

    baseline_impl_name = "OpenCilk+PBBS+2048+cg"
    baseline_impl_name = getImplNameArg(baseline_impl_name)

    myKeys = list(list_of_results[baseline_impl_name].keys())
    myKeys.sort()

    # Represent table as list of a list
    table_result = []
    table_result.append([])
    table_result[0].append("Benchmark")
    table_result[0].append("Dataset")
    table_result[0].append("Num Cores")
    
    if(icache):
        table_result[0].append(f'{baseline_impl_name}{perc}')
    else:        
        table_result[0].append(f'{baseline_impl_name}(s)')
    
    for impl in set_of_impl:        
        if ignore_impl(impl, baseline_impl_name, tex):
            continue
        table_result[0].append(f'{impl} ({perc})')
        
    geomean_res = {} 
    max_res = {}
    min_res = {}
    i = 1
    
    for key1 in myKeys:
        for key2 in list_of_results[baseline_impl_name][key1]:
            for key3 in list_of_results[baseline_impl_name][key1][key2]:
                table_result.append([])
                table_result[i].append(key1)
                table_result[i].append(key2)
                table_result[i].append(key3)
                
                baselinesamples = list_of_results[baseline_impl_name][key1][key2][key3]
                
                baselineavg = 0;

                if(icache):
                    imisses = baselinesamples[samples-2];
                    ihits = baselinesamples[samples-1]
                    baselineavg = calculate_mr(imisses, ihits)
                else:
                    baselineavg = statistics.mean(baselinesamples[0:samples])
                
                if(baselineavg < 0):
                    table_result[i].append("N/A")
                else:
                    table_result[i].append(format(baselineavg, fp_format))
                for impl in set_of_impl:
                    if ignore_impl(impl, baseline_impl_name, tex):
                        continue

                    if key1 in list_of_results[impl]:
                        if key2 in list_of_results[impl][key1]:
                            if key3 in list_of_results[impl][key1][key2]:
                                othersample =  list_of_results[impl][key1][key2][key3]
                                otheravg = 0
                                
                                if(icache):
                                    imisses = othersample[samples-2];
                                    ihits = othersample[samples-1]
                                    otheravg = calculate_mr(imisses, ihits)
                                else:
                                    otheravg = statistics.mean(othersample[0:samples])
                       
                                if(baselineavg <= 0 or baselineavg == "N/A"):
                                    table_result[i].append("N/A")
                                elif otheravg <= 0:
                                    table_result[i].append("N/A")
                                else:
                                    perf_improvement = 0;
                                    if (icache):
                                        perf_improvement = abs(baselineavg - otheravg)
                                    else:
                                        perf_improvement = (baselineavg - otheravg)/baselineavg * 100
                                    
                                    table_result[i].append(f'{format(perf_improvement, fp_format)} {perc}')
                                    
                                    if impl not in max_res:
                                        max_res[impl] = perf_improvement
                                    else:
                                        if(perf_improvement > max_res[impl]):
                                            max_res[impl] = perf_improvement

                                    if impl not in min_res:
                                        min_res[impl] = perf_improvement
                                    else:
                                        if(perf_improvement < min_res[impl]):
                                            min_res[impl] = perf_improvement

                                    if impl not in geomean_res:
                                        geomean_res[impl] = []
                                    geomean_res[impl].append(perf_improvement/100+1)
                    

                i = i + 1

    # Add min
    table_result.append([])
    table_result[i].append("Min")
    table_result[i].append("")
    table_result[i].append("")
    table_result[i].append("")
    for impl in set_of_impl:
        if ignore_impl(impl, baseline_impl_name, tex):
            continue        
        table_result[i].append(f'{format(min_res[impl], fp_format)} {perc}')

    i = i+1

    # Add geomean
    table_result.append([])
    table_result[i].append("Geomean")
    table_result[i].append("")
    table_result[i].append("")
    table_result[i].append("")
    for impl in set_of_impl:
        if ignore_impl(impl, baseline_impl_name, tex):
            continue        
        table_result[i].append(f'{format((gmean(geomean_res[impl])-1)*100, fp_format)} {perc}')
    i = i+1

    # Add max
    table_result.append([])
    table_result[i].append("Max")
    table_result[i].append("")
    table_result[i].append("")
    table_result[i].append("")
    for impl in set_of_impl:
        if ignore_impl(impl, baseline_impl_name, tex):
            continue        
        table_result[i].append(f'{format(max_res[impl], fp_format)} {perc}')

    return table_result
        
# Read the csv result
def getresult(input_file):
  myfile = open(input_file)
  csvreader = csv.reader(myfile)

  list_of_results = {}

  set_of_impl = set()

  # Get the results
  for row in csvreader:
    benchmark_name = row[int(ColName.BENCHMARK)]

    # Skip if empty data or header
    if(benchmark_name == "" or benchmark_name == "BENCHMARK"):
        continue

    #benchname = benchmark_name.replace('\\/', '-')
    benchname = benchmark_name.split('/')
    benchname = f'{benchname[1]}-{benchname[2]}'

    # Get the actual benchmark name
    compiles = row[int(ColName.COMPILES)]
    dataset = row[int(ColName.DATASET)].replace('_', '-')
    num_cores = row[int(ColName.NUM_CORES)]
    status = row[int(ColName.STATUS)]
    disable_numa = row[int(ColName.DISABLE_NUMA)]
    parallel_framework = row[int(ColName.PARALLEL_FRAMEWORK)]
    task_scheduler = row[int(ColName.TASK_SCHEDULER)]
    pfor_grainsize = row[int(ColName.PFOR_MAXGRAINSIZE)]
    ignore_user_grainsize = row[int(ColName.IGNORE_USERS_PFORGRAINSIZE)]
    time = row[int(ColName.TIME):len(row)-1]
    err = row[int(ColName.ERROR_MSG)]
    
    cg = "cg"
    if(ignore_user_grainsize == "Yes"):
        cg = "nocg"
    
    name_of_impl = f"{parallel_framework}+{task_scheduler}+{pfor_grainsize}+{cg}"
    name_of_impl = getImplNameArg(name_of_impl)
    set_of_impl.add(name_of_impl)

    if(name_of_impl not in list_of_results):
        list_of_results[name_of_impl] = {}
    
    if(benchname not in list_of_results[name_of_impl]):
        list_of_results[name_of_impl][benchname] = {}
        list_of_results[name_of_impl][benchname][dataset] = {}
    
    if(dataset not in list_of_results[name_of_impl][benchname]):
        list_of_results[name_of_impl][benchname][dataset] = {}
        
    num_time = [-1] * len(time)
    if(not (err in ["Verification failed", "Benchmark failed to run"])):
        num_time = [ float(val) if val or val.isnumeric() else -1 for val in time]

    list_of_results[name_of_impl][benchname][dataset][num_cores] = (num_time)
  
  myfile.close()
  return set_of_impl, list_of_results, len(time)

def generate_table(table_results, tex):
    if(tex):
        # Write table 
        i = 0
        for row in table_results:
            if(i == 0):
                print("\\toprule")
            elif(i == 1):
                print("\\midrule")
            j = 0;
            for col in row:
                print(col, end=" ")
                if(j == len(row)-1):
                    print (" \\\\ ", end= " ")
                else:
                    print (" & ", end= " ")
                j = j + 1
            print("")
            i = i + 1
    else:
        for row in table_results:
            j = 0;
            for col in row:
                print(col, end=" ")
                if(j == len(row)-1):
                    print ("", end= " ")
                else:
                    print (",", end= " ")
                j = j + 1
            print("")


def main():
    # Pargse the argument
    parser = argparse.ArgumentParser(description='Option to ')
    parser.add_argument("--ifile", required=True, help="CSV to analyze")    
    parser.add_argument("--icache", action='store_true', help="Analyze the icache misses")
    parser.add_argument("--tex", action='store_true', help="Generate in latex format. Default is csv")    

    
    flags = parser.parse_args()
    ifile = flags.ifile
    tex = flags.tex
    icache = flags.icache
    
    if(icache):
        fp_format = '.5f'

    # Read the files
    set_of_impl, results, samples = getresult(ifile);
    
    # Do the processing
    table_results = process_results(set_of_impl, results, samples, tex, icache)

    # Generate table
    generate_table(table_results, tex)
    
# Main entry
main()
