# Getting started

1. Pull the docker image :

```console
docker pull cpakha/lazydcompiler:latest
```

2. Run the docker using :

```console
docker run --privileged -v <host_directory>:/home/user/lazyDir -it cpakha/lazydcompiler:latest
```

# Setting up the folders

Execute :

```conosle
/home/user/setup.sh
```

This setup the directory needed for evaluation in the host directory (/home/user/lazyDir).

# Navigating important directories
After setup.sh, lazyDir contains 3 directories: cilkbench, opencilk, and pbbsbench
The following our the directories that user most likely interact in lazyDir:

- cilkbench: The cilkbench is the directory where users evaluate LazyD's performance

  - cilk5/: Contains the cilk5 benchmark

  - pbbs_v2/: Contains the PBBSv2 benchmark. It is a soft link to pbbsbench/benchmarks

  - testBenchmark_compile.py : Script to compile and run Cilk5 and PBBSv2 benchmarks.
    			       Refer to our artifact.pdf on how to use the compiler and scripts.

  - compile-cilk.sh and testCilk.sh : Compile the Cilk5 benchmarks

  - rm-all-exes.sh : Remove the generated binaries during compilation

  - run-eval.sh : Evaluate the performance of LazyD and OpenCilk on the Cilk5 and PBBSv2 benchmarks


- pbbsbench

  - benchmarks/: contains the PBBSv2 benchmarks 

  - common/parallelDefs: 

  - parlay/internal/scheduler_plugins/opencilk.h : Contains the implementation of different scheduling mechanism for parallel-for. 

# Running the evaluation
Run 

```console
/home/user/lazyDir/cilkbench/run-eval.sh <Number of workers> <Number of runs> <disable numa>
```

to evaluate the performance of LazyD and OpenCilk.
This will generate data needed for our claim in artifact.pdf