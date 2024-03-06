FROM ubuntu:20.04

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


# Unpack clang installation into this image.
ADD clang.tar.gz /usr/local/
