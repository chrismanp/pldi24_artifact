# build the compiler container
FROM cpakha/lazydcompbase:latest

LABEL maintainer "ULI group"

RUN ln -s /lib/x86_64-linux-gnu/libtinfo.so  /lib/x86_64-linux-gnu/libtinfo.so.5
RUN ln -s /lib/x86_64-linux-gnu/libedit.so /lib/x86_64-linux-gnu/libedit.so.0

# Unpack the runtime library
RUN mkdir opencilk
RUN mkdir opencilk/cheetah/
ADD cheetah.tar.gz /home/user/opencilk/cheetah/

RUN mkdir /home/user/lazydlib
ADD libunwind_scheduler.a /home/user/lazydlib

# Unpack the cilk5 benchmark
ADD cilk5.tar.gz  /home/user

RUN git clone https://github.com/user-level-interrupts/pbbsbench.git /home/user/pbbsbench \
    && cd /home/user/pbbsbench \
    && git checkout pldi24_artifact

# Set up the environment for executing the code
RUN mkdir /home/user/cilkbench
RUN mkdir /home/user/cilkbench/oDir
RUN mkdir /home/user/lazyDir

WORKDIR /home/user/cilkbench
RUN mv ../cilk5 cilk5

# Move the test script
ADD lazybenchmark.csv           /home/user/cilkbench
ADD lazybenchmark_big.csv       /home/user/cilkbench
ADD justmis.csv                 /home/user/cilkbench
ADD parse_lazybenchmark_csv.py  /home/user/cilkbench
ADD testBenchmark_compile.py    /home/user/cilkbench

ADD configureTests.sh /home/user/cilkbench
ADD parseArgs.sh      /home/user/cilkbench
ADD testCilk.sh       /home/user/cilkbench
ADD compile-cilk.sh   /home/user/cilkbench
ADD rm-all-exes.sh    /home/user/cilkbench
ADD run-eval.sh       /home/user/cilkbench

RUN chmod +x          /home/user/cilkbench/testCilk.sh
RUN chmod +x          /home/user/cilkbench/run-eval.sh

# From cilk5's Makefile
ADD Makefile          /home/user/cilkbench/cilk5

WORKDIR /home/user
COPY setup.sh /home/user/setup.sh
RUN chmod +x /home/user/setup.sh
CMD ["/bin/bash"]