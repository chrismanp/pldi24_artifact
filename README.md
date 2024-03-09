# Introduction

LazyD is compiler and runtime that compiles a Cilk code and generate low overhead fork-joins and parallel-loop.

# Trying LazyD on a Docker

1. Pull the docker image :

```console
docker pull cpakha/lazydcompiler:latest
```

2. Run the docker using :

```console
docker run --privileged -v <host_directory>:/home/user/lazyDir -it cpakha/lazydcompiler:latest
```

3. Setting up the folders

Execute :

```console
/home/user/setup.sh
```

This setup the directory needed for evaluation in the host directory (/home/user/lazyDir).

# Navigating important directories
After setup.sh, lazyDir contains 3 directories: cilkbench, opencilk, and pbbsbench
The following our the directories that user most likely interact in lazyDir:

- cilkbench: The cilkbench is the directory where users evaluate LazyD's performance

  - cilk5/: Contains the cilk5 benchmark.

  - pbbs_v2/: Contains the PBBSv2 benchmark. It is a soft link to pbbsbench/benchmarks.

  - testBenchmark_compile.py : Script to compile and run Cilk5 and PBBSv2 benchmarks.
    			       Refer to our artifact.pdf on how to use the compiler and scripts.

  - compile-cilk.sh and testCilk.sh : Compiles the Cilk5 benchmarks.

  - rm-all-exes.sh : Removes the generated binaries during compilation.

  - run-eval.sh : Evaluates the performance of LazyD and OpenCilk on the Cilk5 and PBBSv2 benchmarks.

  - oDir/ : Stores the result of the executing the testBenchmark_compile.py

  - oDir/lazybenchmark_output_files*/lazbenchmark_results.csv : Stores the result of the evaluation as a CSV file.

  - lazybenchmark.csv : Stores the benchmark that testBenchmark_compile.py used to compile and execute.

- pbbsbench

  - benchmarks/: Contains the PBBSv2 benchmarks.

  - pbbsbench/testData/sequenceData/: Stores the dataset for sequence problem.

  - pbbsbench/testData/graphData/: Stores the dataset for graph problem.

  - pbbsbench/testData/geometryData/: Stores the dataset for geometry problem.

  - common/parallelDefs: Contains different compiler options that affects the lowering of parallel-for and fork-join.

  - parlay/internal/scheduler_plugins/opencilk.h : Contains the implementation of different scheduling mechanism for parallel-for. 

# Evaluating LazyD Perforamnce against OpenCilk
Run 

```console
/home/user/lazyDir/cilkbench/run-eval.sh <Number of workers> <Number of runs> <disable numa>
```

to evaluate the performance of LazyD and OpenCilk.
This will generate data needed for our claim in artifact.pdf

# Compile your own code

Use the following command to compile your own cilk code

```console
  clang -fforkd=lazy -ftapir=serial -mllvm -noinline-tasks=true \
        -mllvm -experimental-debug-variable-locations=false \
        -mllvm -disable-parallelepilog-insidepfor=true \
        -fuse-ld=lld  --opencilk-resource-dir=../../opencilk/cheetah/build/ \
        -Wall -O3  yourcilkcode.c   -o yourcilkcode
```

# Limitation

- LazyD is only able to compile cilk_for, cilk_spawn, and cilk_sync. It is not able to compile OpenCilk's hyberobject.
- LazyD Parallel-Ready Loop is not the default lowering of parallel-for and needs to be enable using -fpfor-spawn-strategy=2.
- LazyD Parallel-Ready Loop has issue in dealing with non-AddRec Scalar evolution.
- There are still bugs when compiling complicated Cilk code. For that reason LazyD have to disable certain compiler features.