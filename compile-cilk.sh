#!/usr/bin/bash

# compile executable for model if it doesn't exist

# process options
prog=$0
edir=cilk5
verbose=0
force=0
while [ "$#" -gt "0" ]
do
    if [ ${1#-} == $1 ]; then
	break;
    fi
    opt=$1;
    shift;
    case $opt in
	-f)
	    force=1
	    ;;
	-v)
	    verbose=1
	    ;;
	*)
	    echo "Unknown option $opt"
	    echo "$prog [-f][-v] model benchmark"
	    echo " -f: force recompile"
	    echo " -v: verbose"
	    exit -1
	    ;;
    esac
done

# check that model and benchmark are given
if [ $# != 2 ]; then
    echo "Requires 2 arguments, try -h for help"
fi

model=$1
benchmark=$2

target=${edir}/${benchmark}.${model}
if [ $force == 0 ]; then
    if [ -e $target ]; then
	echo "Already Compiled"
	exit 0
    fi
fi
# convert our suffix name into a switch for testCilk compilation
case $model in
    pnnt)
	modelswitch=t
	;;
    pnnuf)
	modelswitch=uf
	;;
    pnnlf)
	modelswitch=f
	;;
    pnnef)
	modelswitch=ef
	;;
    pnns)
	modelswitch=s
	;;
    *)
	echo "Bad model"
	exit -1
	;;
esac
# run compile command
./testCilk.sh -${modelswitch} -x=0 -w=0 ${benchmark}
status=$?
if [ $status == 0 ]; then
    echo "Saving to ${target}"
    /bin/mv ${edir}/${benchmark} ${target}
else
    echo "Failed to compile"
fi
exit $status
