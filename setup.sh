#!/usr/bin/env bash

# Create the required directory

if [ ! -d /home/user/lazyDir/cilkbench ]; then
    echo "Directory /home/user/lazyDir/cilkbecng does not exists!"
    echo "cp -r /home/user/cilkbench /home/user/lazyDir/"
    cp -r /home/user/cilkbench /home/user/lazyDir/
fi

if [ ! -d /home/user/lazyDir/pbbsbench ]; then
    echo "Directory /home/user/lazyDir/pbbsbench does not exists!"
    echo "cp -r /home/user/pbbsbench /home/user/lazyDir/"
    cp -r /home/user/pbbsbench /home/user/lazyDir/
    echo "ln -s /home/user/lazyDir/pbbsbench/benchmarks /home/user/lazyDir/cilkbench/pbbs_v2"
    ln -s /home/user/lazyDir/pbbsbench/benchmarks /home/user/lazyDir/cilkbench/pbbs_v2
fi

if [ ! -d /home/user/lazyDir/opencilk ]; then
    echo "Directory /home/user/lazyDir/opencilk does not exists!"
    echo "cp -r /home/user/opencilk /home/user/lazyDir/"
    cp -r /home/user/opencilk /home/user/lazyDir/
fi
