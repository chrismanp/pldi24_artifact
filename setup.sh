#!/usr/bin/env bash

# Perform linking of different folder
ln -s /lib/x86_64-linux-gnu/libtinfo.so  /lib/x86_64-linux-gnu/libtinfo.so.5
ln -s /lib/x86_64-linux-gnu/libedit.so /lib/x86_64-linux-gnu/libedit.so.0
ln -s /home/user/pbbsbench/benchmarks /home/user/cilkbench/pbbs_v2
