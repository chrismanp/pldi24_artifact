COMPILERS="gcc tapir ref stapir sref serial lazyfork ulifork uipifork sigusrfork eagerdfork"
WORKERS="1 18"
# NUMTRIALS=3

TAPIR_CC=clang
TAPIR_CXX=clang++

#TAPIR_CC=/afs/ece/project/seth_group/pakha/my-opencilk-repo/build/bin/clang
#TAPIR_CXX=/afs/ece/project/seth_group/pakha/my-opencilk-repo/build/bin/clang++

#/afs/ece/project/seth_group/pakha/my-opencilk-repo/build/bin/clang -ftapir=opencilk --opencilk-resource-dir=../../opencilk/cheetah/build/ -O3 fib.c -o fib

#TAPIR_CC=/afs/ece/project/seth_group/pakha/uli/src/compiler/build/bin/clang
#TAPIR_CXX=/afs/ece/project/seth_group/pakha/uli/src/compiler/build/bin/clang++

#TAPIR_CC=/afs/ece/project/seth_group/pakha/opencilk/opencilk-project/build/bin/clang
#TAPIR_CXX=/afs/ece/project/seth_group/pakha/opencilk/opencilk-project/build/bin/clang++

if [ -z $REF_BASE ]; then
    if [ -z $TAPIR_BASE ]; then
	REF_BASE="/unknown/path/to/src-ref"
    else
	REF_BASE=$TAPIR_BASE-ref
    fi
fi

if [ ! -z $TAPIR_BASE ]; then
    if [ -z $DEBUG ]; then
	TAPIR_ROOT=$TAPIR_BASE/build
	REF_ROOT=$REF_BASE/build
    else
	echo "Using Debug build"
	TAPIR_ROOT=$TAPIR_BASE/build-debug
	REF_ROOT=$REF_BASE/build-debug
    fi
fi

if [ ! -z $TAPIR_ROOT ]; then
    TAPIR_PATH=$TAPIR_ROOT/bin
    REF_PATH=$REF_ROOT/bin

    TAPIR_CC=$TAPIR_PATH/clang
    TAPIR_CXX=$TAPIR_PATH/clang++

    TAPIR_LIB=$TAPIR_ROOT/lib/clang/`$TAPIR_CC --version | perl -pe '($_)=/([0-9]+([.][0-9]+)+)/'`/lib/linux
else
    TAPIR_LIB=/usr/lib/clang/`$TAPIR_CC --version | perl -pe '($_)=/([0-9]+([.][0-9]+)+)/'`/lib/linux
fi
echo $TAPIR_LIB

# ../../uli-runtime/ext_lib/libpfm_build/lib/libpfm.a"

LAZYD_CILK_FLAG="-fforkd=lazy -ftapir=serial -mllvm -noinline-tasks=true -mllvm -experimental-debug-variable-locations=false -mllvm -disable-parallelepilog-insidepfor=true  -fuse-ld=lld -O3"


#ULI_CILK_FLAG="$LAZYD_CILK_FLAG -mllvm -lazy-poll-lowering=unwind-ulifsim -mllvm -lazy-enable-proper-polling=0 -mllvm -lazy-set-maxgrainsize=2048 -Xclang -fpfor-spawn-strategy=1 -mllvm -lazy-set-maxinstpoll=1"

ULI_CILK_FLAG="$LAZYD_CILK_FLAG  --opencilk-resource-dir=../../opencilk/cheetah/build/"

#ULI_CILK_FLAG="-ftapir=serial -fuse-ld=lld ../../uli-runtime/ext_lib/libpfm_build/lib/libpfm.a -fpfor-spawn-strategy=1"

#ULI_CILK_FLAG="$LAZYD_CILK_FLAG -mllvm -lazy-poll-lowering=nop -mllvm -lazy-disable-unwind-polling=true -mllvm -lazy-enable-proper-polling=0 -mllvm -lazy-set-maxgrainsize=2048 -fpfor-spawn-strategy=1 -mllvm -lazy-set-maxinstpoll=1"


#ULI_CILK_FLAG="$LAZYD_CILK_FLAG -DSTATS_OVER_TIME -mllvm -lazy-poll-lowering=unwind-ulifsim -mllvm -lazy-enable-proper-polling=0 -mllvm -lazy-set-maxgrainsize=2048 -Xclang -fpfor-spawn-strategy=1 -mllvm -lazy-set-maxinstpoll=1 -mllvm -enable-poll-epoch=true -mllvm -lazy-enable-main-instrumentation=false"
UIPI_CILK_FLAG="-fforkd=uli -ftapir=serial -fuse-ld=lld -mllvm -lazy-poll-lowering=nop -mllvm -disable-lazy-endisui=true  --opencilk-resource-dir=../../opencilk/cheetah/build/"
#UIPI_CILK_FLAG="-fforkd=uli -ftapir=serial -fuse-ld=lld -mllvm -lazy-poll-lowering=nop -mllvm -enable-lazy-stuiclui=true"
SIGUSR_CILK_FLAG="-fforkd=sigusr -ftapir=serial -fuse-ld=lld -mllvm -lazy-poll-lowering=nop -mllvm -disable-lazy-endisui=true "
EAGERD_CILK_FLAG="-fforkd=eager -ftapir=serial -fuse-ld=lld -fno-omit-frame-pointer  -mno-omit-leaf-frame-pointer -mllvm -eager-set-maxgrainsize=2048 -mllvm -enable-poll-epoch=false"
#EAGERD_CILK_FLAG="-fforkd=eager -ftapir=serial -fuse-ld=lld -fno-omit-frame-pointer  -mno-omit-leaf-frame-pointer -mllvm -enable-poll-epoch=true "
#TAPIR_CILK_FLAG="-fcilkplus -mllvm -cilk-set-maxgrainsize=2048 -ldl"
TAPIR_CILK_FLAG="-fopencilk --opencilk-resource-dir=../../opencilk/cheetah/build/ -ldl"

REF_CILK_FLAG=-fcilkplus #-fdetach
GCC_CILK_FLAG=-fcilkplus

SERIAL_CFLAGS="-Dcilk_for=for -Dcilk_spawn=  -Dcilk_sync=  -D_Cilk_for=for -D_Cilk_spawn=  -D_Cilk_sync= "
REPORT_CFLAGS="-Rpass=.* -Rpass-analysis=.*"
# REPORT_CFLAGS="-Rpass=loop-spawning"

CILKSAN_LIB=$TAPIR_LIB
CILKSAN_CFLAGS="-g -fsanitize=cilk"
# CILKSAN_LDFLAGS="-lcilksan -L$CILKSAN_LIB"
CILKSAN_LDFLAGS="-fsanitize=cilk"

CILKSCALE_CFLAGS="-flto -fcsi"
CILKSCALE_LDFLAGS="-flto -fuse-ld=gold -L$TAPIR_LIB"
CILKSCALE_LDLIBS="-lclang_rt.cilkscale-x86_64"

JEMALLOC_LDLIBS="-L`jemalloc-config --libdir` -Wl,-rpath,`jemalloc-config --libdir` -ljemalloc `jemalloc-config --libs`"

C_COMPILER() {
    case $1 in
	"tapir") echo "$TAPIR_CC $TAPIR_CILK_FLAG";;
	"ref") echo "$REF_PATH/clang $REF_CILK_FLAG";;
	"stapir") echo "$TAPIR_CC $TAPIR_CILK_FLAG $SERIAL_CFLAGS";;
	"sref") echo "$REF_PATH/clang $REF_CILK_FLAG $SERIAL_CFLAGS";;
	"serial") echo "$TAPIR_CC $SERIAL_CFLAGS";;
	"lazyfork") echo "$TAPIR_CC $LAZYD_CILK_FLAG";;
	"ulifork") echo "$TAPIR_CC $ULI_CILK_FLAG";;
	"uipifork") echo "$TAPIR_CC $UIPI_CILK_FLAG";;
	"sigusrfork") echo "$TAPIR_CC $SIGUSR_CILK_FLAG";;
	"eagerdfork") echo "$TAPIR_CC $EAGERD_CILK_FLAG";;
	"gcc") echo "gcc $GCC_CILK_FLAG";;
	"sgcc") echo "gcc $GCC_CILK_FLAG $SERIAL_CFLAGS";;
	*) echo "Unknown compiler $1"; exit 1;;
    esac
}

CXX_COMPILER() {
    case $1 in
	"tapir") echo "$TAPIR_CXX $TAPIR_CILK_FLAG";;
	"ref") echo "$REF_PATH/clang++ $REF_CILK_FLAG";;
	"stapir") echo "$TAPIR_CXX $TAPIR_CILK_FLAG $SERIAL_CFLAGS";;
	"sref") echo "$REF_PATH/clang++ $REF_CILK_FLAG $SERIAL_CFLAGS";;
	"serial") echo "$TAPIR_CXX $SERIAL_CFLAGS";;
	"lazyfork") echo "$TAPIR_CXX $LAZYD_CILK_FLAG";;
	"ulifork") echo "$TAPIR_CXX $ULI_CILK_FLAG";;
	"uipifork") echo "$TAPIR_CXX $UIPI_CILK_FLAG";;
	"sigusrfork") echo "$TAPIR_CXX $SIGUSR_CILK_FLAG";;
	"eagerdfork") echo "$TAPIR_CXX $EAGERD_CILK_FLAG";;
	"gcc") echo "g++ $GCC_CILK_FLAG";;
	"sgcc") echo "g++ $GCC_CILK_FLAG $SERIAL_CFLAGS";;
	*) echo "Unknown compiler $1"; exit 1;;
    esac
}

RUN_ON_P_WORKERS() {
    P=$1
    # echo "CILK_NWORKERS=$P setarch x86_64 -R taskset -c 1-$P numactl -i all ionice -c 2 -n 0 $2"
    # CILK_NWORKERS=$P setarch x86_64 -R taskset -c 1-$P numactl -i all ionice -c 2 -n 0 $2

    # ECE private machine does not have ionice command
    #echo "CILK_NWORKERS=$P setarch x86_64 -R taskset -c 1-$P numactl -i all ionice -c 2 -n 0 $2"
    #CILK_NWORKERS=$P setarch x86_64 -R taskset -c 1-$P numactl -i all ionice -c 2 -n 0 $2

    echo "CILK_NWORKERS=$P $2"
    CILK_NWORKERS=$P $2
}
