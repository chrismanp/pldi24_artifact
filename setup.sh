#!/usr/bin/env bash

# Create the required directory

if [ ! -d /home/user/lazyDir/pbbsbench ]; then
    echo "Creating /home/user/lazyDir/pbbsbench"
    cp -r /home/user/pbbsbench /home/user/lazyDir/
fi

if [ ! -d /home/user/lazyDir/cilkbench ]; then
    echo "Creating /home/user/lazyDir/cilkbench"
    cp -r /home/user/cilkbench /home/user/lazyDir/
    ln -s /home/user/lazyDir/pbbsbench/benchmarks /home/user/lazyDir/cilkbench/pbbs_v2
fi


if [ ! -d /home/user/lazyDir/opencilk ]; then
    echo "Creating /home/user/lazyDir/opencilk"
    cp -r /home/user/opencilk /home/user/lazyDir/
fi
