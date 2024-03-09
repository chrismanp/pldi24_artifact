# Getting started

1. Pull the docker image :

```console
username@machine:~$ docker pull cpakha/lazydcompiler:latest
```

2. Run the docker using :

```console
username@machine:~$ docker run --privileged -v <host_directory>:/home/user/lazyDir -it cpakha/lazydcompiler:latest
```

# Setting up the folders

Execute :

```conosle
username@machine:/home/user/setup.sh
```

To setup the directory needed for execution in the host directory (/home/user/lazyDir).

# Navigating important directories
After setup.sh, lazyDir contains 3 directories: cilkbench, opencilk, and pbbsbench
The following our the directories that user most likely interact in lazyDir:

## cilkbench
The cilkbench is the directory where users evaluate the performance of LazyD.

1. cilk5/: Contains the cilk5 benchmark

2. pbbs_v2/: Contains the PBBSv2 benchmark. It is a softlink to pbbsbench/benchmarks

3. testBenchmark_compile.py : Script to compile and run Cilk5 and PBBSv2 benchmarks.

4. compile-cilk.sh and testCilk.sh : Compile cilk5 codes

5. rm-all-exes.sh : Remove the generated binaries during compilation

6. run-eval.sh : Run experiment on the cilk5 and PBBSv2 benchmark to evaluate the performance of LazyD 


## PBBSBench

1. benchmarks/: contains the benchmark 

2. common/parallelDefs: 

3. parlay/internal/scheduler_plugins/opencilk.h : Contains the implementation of different scheduling mechanism for parallel-for. 

# Running the evaluation
Run 

```console
username@machine:/home/user/run-eval.sh <Number of workers> <Number of runs> <disable numa>
```

This will genenerate data needed for our claim in artifact.pdf

# Other options

Refer to our artifact.pdf on how to use the compiler and scripts.
