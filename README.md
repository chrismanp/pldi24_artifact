# Introduction of LazyD

LazyD is a compiler and runtime for programs written in Cilk.  The
compiler converts fork-join and parallel-for constructs into low
overhead parallel-ready sequential code.  Parallelism is realized via
work requests.  Hence, the control overhead of managing parallel
constructs is virtually eliminated when parallelism is not needed.
LazyD attempts to improve the performance of a parallel program when
the overhead of the parallel construct is significant and when using a
coarser grain size can cause load imbalance on a higher core count.
It relies on stack-walking, code-versioning, and polling to generate
low-overhead parallel constructs.  It is built on top of the OpenCilk
compiler and takes advantage of Tapir.

Refer to [artifact-desc](artifact-desc.pdf) for a full description of our artifacts.

# Trying LazyD on a Docker

We provide a docker image so users can try out LazyD using their own Cilk code.  
The following are the instructions for setting up the docker
image.

1. Pulling the docker image :

```console
docker pull cpakha/lazydcompiler:latest
```

2. Running the docker:

```console
docker run --privileged -v <host_directory>:/home/user/lazyDir -it cpakha/lazydcompiler:latest
```

We recommend the following options with the docker run command:

- --user=<uid>:<gid> This will set the user ID to <uid> and the group ID to <gid>.
- --rm Remove the container once the docker has been exited

3. Setting up the folders:

```console
/home/user/setup.sh
```

This sets up the directory needed for evaluation in the host directory (/home/user/lazyDir).

## Navigating important directories

After running `setup.sh`, [lazyDir](./lazyDir) will contain three
directories: cilkbench, opencilk, and pbbsbench.  The following are
the directories that users are most likely to interact within
lazyDir:

- cilkbench: The cilkbench is the directory where users evaluate LazyD's performance

  - cilk5/: Contains the cilk5 benchmark.

  - pbbs_v2/: Contains the PBBSv2 benchmark. It is a soft link to pbbsbench/benchmarks.

  - testBenchmark_compile.py : Script to compile and run Cilk5 and PBBSv2 benchmarks.
    			       Refer to our [artifact-desc](artifact-desc.pdf) on how to use the compiler and scripts.

  - compile-cilk.sh and testCilk.sh : Compiles the Cilk5 benchmarks.

  - rm-all-exes.sh : Removes the generated binaries during compilation.

  - run-{eval,icache}.sh : Evaluates the performance of LazyD and OpenCilk on the Cilk5 and PBBSv2 benchmarks.

  - oDir/ : Stores the result of the executing the testBenchmark_compile.py

  - oDir/lazybenchmark_output_files*/lazbenchmark_results.csv : Stores the result of the evaluation as a CSV file.

  - oDir/lazybenchmark_output_files*/log.txt : Logs the execution of testBenchmark_compile.py.

  - lazybenchmark.csv : Stores the benchmark that testBenchmark_compile.py used to compile and execute.

  - analyzecsv.py : Analyze the result from running run-{eval,icache}.sh

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
2) Exposing more parallelism using LazyD does not degrade performance on average.
3) For programs with irregular parallelism, LazyD prevents load imbalance by exposing more parallelism.
4) LazyD does not adversely impact the I-Cache miss rate.

To evaluate our claim, run the following command in the lazyDir/cilkbench directory:

```console
/home/user/lazyDir/cilkbench/run-eval.sh <Number of workers> <Number of runs> <disable numa>
/home/user/lazyDir/cilkbench/run-icache.sh <Number of workers> <Number of runs> <disable numa>
```

The above script relies on the testBenchmark_compile.py script.
The following are the flags that testBenchmark_compile.py supports:

```console
options:
  -h, --help            show this help message and exit
  --compile             Only compile the benchmark
  --num_cores NUM_CORES [NUM_CORES ...]
                        Number of cores used. Default: 1
  --num_tests NUM_TESTS
                        Number of runs per test
  --execute             Only execute benchmark, do not compile
  --disable_numa        Do not use numactl --interleave=all when running the benchmark
  --icache              Run the icache experiment
  --parallel_framework {lazyd0,lazyd2,nopoll,serial,tapir} [{lazyd0,lazyd2,nopoll,serial,tapir} ...]
                        The parallel framework to use. Default: tapir.

			lazyd0 = LazyD with infrequent polling (sets env variable POLL0=1)
                        lazyd2 = LazyD with frequent polling   (sets env variable POLL2=1)
                        nopoll = LazyD without polling         (sets env variable NOPOLL=1)
                        serial = Sequential program            (sets env variable SEQUENTIAL=1)
                        tapir = OpenCilk program               (sets env variable OPENCILK=1)

  --fg {yes,no,both}    Use finer grainsize. Default: no
                        If --noopt is false, user grainsize does not get affected.
                        Only used by PRC, PRL, DELEGATEPRC, PRCPRL, DELEGATEPRCPRL,
                        and OPENCILKDEFAULT_FINE.  (sets env variable GRAINSIZE8=1)

  --noopt {yes,no,both}
                         Ignore parallel-for's grainsize set by the user. Default: no
                         Only used in PBBS and DELEGATEPRCPRL.  (sets env variable NOOPT=1)

  --schedule_tasks {PRC,PRL,DELEGATEPRC,PRCPRL,DELEGATEPRCPRL,OPENCILKDEFAULT_FINE,PBBS} [{PRC,PRL,DELEGATEPRC,PRCPRL,DELEGATEPRCPRL,OPENCILKDEFAULT_FINE,PBBS} ...]
                        How to schedule parallel task in pfor. Only used for the PBBSv2 benchmarks.

			PBBS : By default, it uses the PBBS scheduling mechanism.
                        The PBBS default scheduling mechanism uses divide and conquer 
                        if the grainsize is not equal to 0.
                        If grainsize is set to 0, it uses cilk_for parallel construct.

                        OPENCILKDEFAULT_FINE: Similar to PBBS. 
                        However, if the grainsize is set to 0, 
			the maximum grainsize is set to 8 
			(Default value used by PBBS is 2048).
                        (sets environment variable OPENCILKDEFAULT_FINE=1)

                        PRC: Similar to PBBS, except that we manually 
                        lower the cilk_for in the source code using divide and conquer
			with tail call elimination.
                        (sets environment variable PRC=1)

                        PRL: Use parallel-ready loop to lower the parallel-for. 
                        (sets env variable PRL=1)

                        PRCPRL : Uses PRC and then PRL
                        for the remaining iteration. (sets env variable PRCPRL=1)

                        DELEGATEPRC :  Uses Explicit fork and then PRC 
                        for the remaining iteration.
                        (sets env variable DELEGATEPRC=1)

                        DELEGATEPRCPRL :  Uses Explicit fork, 
                        then PRC, and then PRL for the remaining iteration. 
                        (sets environment variable DELEGATEPRCPRL=1)

  --ifile IFILE         Input file
  -v, --verbose         Verbose
  --dryrun              Dry run, only print commands that would be executed
  --wait_load WAIT_LOAD The minimum load before the benchmark can be executed (Default=10)

```

This will generate the data needed for our claim in [artifact-desc](artifact-desc.pdf).
Refer to [artifact-desc](artifact-desc.pdf) to test our claim.

# Compile your own code
If users are interested in evaluating LazyD performance on their own Cilk code, use the following command:

```console
  clang -fforkd=lazy -ftapir=serial -mllvm -noinline-tasks=true \
        -mllvm -experimental-debug-variable-locations=false \
        -mllvm -disable-parallelepilog-insidepfor=true \
        -fuse-ld=lld  --opencilk-resource-dir=../../opencilk/cheetah/build/ \
        -Wall -O3  yourcilkcode.c   -o yourcilkcode
```

The [artifact-desc](artifact-desc.pdf) provides a list of the compiler's options.
Running the program can be done by simply executing:

```console
  CILK_NWORKERS=<number of cores> ./yourcilkcode <..,args,..>
```

# Limitation

- LazyD is only able to compile cilk_for, cilk_spawn, and cilk_sync. It is not able to compile OpenCilk's hyberobject.
- LazyD's Parallel-Ready Loop is not the default lowering of parallel-for and needs to be enabled using -fpfor-spawn-strategy=2.
- LazyD can not convert parallel loops with non-Add Recurrence evolution.
- LazyD can not compile a parallel region inlined inside another parallel region. For this reason, LazyD has the option to prevent the inliner from inlining a function that contains a parallel region into another parallel region. This is controlled by the `-mllvm -disable-parallelepilog-insidepfor` and `-mllvm -noinline-tasks` flag. The default value is false.
- There are still cases where LazyD may fail to compile complex fork-joins or parallel-for. For a quick fix, isolate these fork-joins or parallel-for into their own function.
