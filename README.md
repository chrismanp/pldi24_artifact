# Introduction of LazyD

LazyD is a compiler and runtime that compiles a Cilk code, generating low-overhead fork-joins and parallel-for, and creates parallelism on a request from an idle thread.
Hence, the control overhead of managing parallel constructs is eliminated when parallelism is not needed.
LazyD attempts to improve the performance of a parallel program when the overhead of the parallel construct is significant
and when using a coarser grain size can cause load imbalance on a higher core count.
It relies on stack-walk, code-versioning, and polling to generate low-overhead parallel constructs.
It is built on top of the OpenCilk compiler and takes advantage of Tapir optimization.

# Trying LazyD on a Docker

We provide a docker image that users can use to try out LazyD on their own Cilk code.
The following are the instructions for setting up the docker image.

1. Pulling the docker image :

```console
docker pull cpakha/lazydcompiler:latest
```

2. Running the docker:

```console
docker run --privileged -v <host_directory>:/home/user/lazyDir -it cpakha/lazydcompiler:latest
```

We recommend the following options when the docker:

- --user=<uid>:<gid> This will set the user ID to <uid> and the group ID to <gid>. 
- --rm Remove the container once the docker has been exited

3. Setting up the folders:

```console
/home/user/setup.sh
```

This sets up the directory needed for evaluation in the host directory (/home/user/lazyDir).

## Navigating important directories

After setup.sh, lazyDir contains three directories: cilkbench, opencilk, and pbbsbench.
The following are the directories that users most likely interact in lazyDir:

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

  - oDir/lazybenchmark_output_files*/log.txt : Logs the execution of testBenchmark_compile.py.

  - lazybenchmark.csv : Stores the benchmark that testBenchmark_compile.py used to compile and execute.

- pbbsbench

  - benchmarks/: Contains the PBBSv2 benchmarks.

  - pbbsbench/testData/sequenceData/: Stores the dataset for sequence problem.

  - pbbsbench/testData/graphData/: Stores the dataset for graph problem.

  - pbbsbench/testData/geometryData/: Stores the dataset for geometry problem.

  - common/parallelDefs: Contains different compiler options that affect the lowering of parallel-for and fork-join.

  - parlay/internal/scheduler_plugins/opencilk.h : Contains the implementation of different scheduling mechanism for parallel-for. 

# Evaluating LazyD Performance

We claim that LazyD has 

1) LazyD’s parallel construct has a smaller overhead compared to OpenCilk's.
2) Exposing more parallelism using LazyD’s does not significantly degrade performance on average.
3) LazyD prevents load imbalance by exposing more parallelism.
4) LazyD’s ICache miss rate is similar to OpenCilk’s.

To evaluate our claim, run the following command in the lazyDir/cilkbench directory:

```console
/home/user/lazyDir/cilkbench/run-eval.sh <Number of workers> <Number of runs> <disable numa>
/home/user/lazyDir/cilkbench/run-icache.sh <Number of workers> <Number of runs> <disable numa>
```

This will generate the data needed for our claim in artifact.pdf

# Compile your own code
If users are interested in evaluating LazyD performance on their own Cilk code, use the following command:

```console
  clang -fforkd=lazy -ftapir=serial -mllvm -noinline-tasks=true \
        -mllvm -experimental-debug-variable-locations=false \
        -mllvm -disable-parallelepilog-insidepfor=true \
        -fuse-ld=lld  --opencilk-resource-dir=../../opencilk/cheetah/build/ \
        -Wall -O3  yourcilkcode.c   -o yourcilkcode
```

The artifact.pdf provides an exhaustive list of the compiler's options.
Currently, lazyD still depends on the opencilk-resource-dir parameter for locating the cilk header.
Running the program can be done by simply executing:

```console
  CILK_NWORKERS=<number of cores> ./yourcilkcode <..,args,..>
```

# Limitation

- LazyD is only able to compile cilk_for, cilk_spawn, and cilk_sync. It is not able to compile OpenCilk's hyberobject.
- LazyD Parallel-Ready Loop is not the default lowering of parallel-for and needs to be enabled using -fpfor-spawn-strategy=2.
- LazyD Parallel-Ready Loop has an issue in dealing with non-AddRec Scalar evolution.
- There are still bugs when compiling complicated Cilk code. For that reason, LazyD has to turn off certain compiler features.
- There are still cases where it may fail to compile complex fork-joins or parallel-for. For a quick fix, isolate these fork-joins or parallel-for into their own function.
 