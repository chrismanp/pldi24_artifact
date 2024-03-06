# build the compiler container
FROM ubuntu:20.04

LABEL maintainer "ULI group"

ENV PATH=$PATH:/usr/local/build/bin/
ENV LIBRARY_PATH=$LIBRARY_PATH:/home/user/lazydlib
ENV TZ=US

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get -y update
RUN apt-get -y install git emacs gcc python g++ ccache make texinfo bison flex python3 cmake libedit-dev libnuma-dev numactl linux-tools-common linux-tools-generic
RUN apt-get -y update

RUN apt-get install -y software-properties-common
RUN add-apt-repository -y ppa:ubuntu-toolchain-r/test
RUN apt install -y g++-11

#RUN ln -s /lib/x86_64-linux-gnu/libtinfo.so  /lib/x86_64-linux-gnu/libtinfo.so.5
#RUN ln -s /lib/x86_64-linux-gnu/libedit.so /lib/x86_64-linux-gnu/libedit.so.0

# Unpack clang installation into this image.
ADD clang.tar.gz /usr/local/

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

WORKDIR /home/user/cilkbench
#RUN ln -s ../pbbsbench/benchmarks pbbs_v2
#RUN mv ../cilk5 cilk5

# Move the test script
ADD lazybenchmark.csv           /home/user/cilkbench
ADD justmis.csv                 /home/user/cilkbench
#ADD lazybenchmark_object.py     /home/user/cilkbench
ADD parse_lazybenchmark_csv.py  /home/user/cilkbench
ADD testBenchmark_compile.py    /home/user/cilkbench

ADD configureTests.sh /home/user/cilkbench
ADD parseArgs.sh      /home/user/cilkbench
ADD testCilk.sh       /home/user/cilkbench

# From cilk5's Makefile
ADD Makefile          /home/user/cilkbench/cilk5

WORKDIR /home/user
COPY setup.sh /home/user/setup.sh
CMD chmod +x /home/user/setup.sh
CMD ["/bin/bash"]