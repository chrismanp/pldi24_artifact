#!/usr/bin/env bash

# Perform linking of different folder
ln -s /lib/x86_64-linux-gnu/libtinfo.so  /lib/x86_64-linux-gnu/libtinfo.so.5
ln -s /lib/x86_64-linux-gnu/libedit.so /lib/x86_64-linux-gnu/libedit.so.0
ln -s /home/user/pbbsbench/benchmarks /home/user/cilkbench/pbbs_v2
ln -s /home/user/pbbsbench/benchmarks /home/user/cilkbench/oDir/pbbs_v2
mv    /home/user/cilk5 /home/user/cilkbench/cilk5
