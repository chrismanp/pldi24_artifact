COMPILERS="gcc tapir ref stapir sref serial lazyd2 lazyd0 uipifork sigusrfork nopoll"
WORKERS="1 18"
# NUMTRIALS=3

TAPIR_CC=clang
TAPIR_CXX=clang++


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

LAZYD_CILK_FLAG="-fforkd=lazy -ftapir=serial -mllvm -noinline-tasks=true -mllvm -experimental-debug-variable-locations=false -mllvm -disable-parallelepilog-insidepfor=true  -fuse-ld=lld"

LAZYD2_CILK_FLAG="$LAZYD_CILK_FLAG -mllvm -lazy-enable-proper-polling=2  --opencilk-resource-dir=../../opencilk/cheetah/build/"

LAZYD0_CILK_FLAG="$LAZYD_CILK_FLAG --opencilk-resource-dir=../../opencilk/cheetah/build/"

NOPOLL_CILK_FLAG="$LAZYD_CILK_FLAG -mllvm -lazy-poll-lowering=nop -mllvm -lazy-disable-unwind-polling=true -mllvm -lazy-disable-unwind-polling2=true --opencilk-resource-dir=../../opencilk/cheetah/build/"

TAPIR_CILK_FLAG="-fopencilk --opencilk-resource-dir=../../opencilk/cheetah/build/ -ldl"

# Not used
UIPI_CILK_FLAG="-fforkd=uli -ftapir=serial -fuse-ld=lld -mllvm -lazy-poll-lowering=nop -mllvm -disable-lazy-endisui=true  --opencilk-resource-dir=../../opencilk/cheetah/build/"
SIGUSR_CILK_FLAG="-fforkd=sigusr -ftapir=serial -fuse-ld=lld -mllvm -lazy-poll-lowering=nop -mllvm -disable-lazy-endisui=true "

REF_CILK_FLAG=-fcilkplus #-fdetach
GCC_CILK_FLAG=-fcilkplus

SERIAL_CFLAGS="-Dcilk_for=for -Dcilk_spawn=  -Dcilk_sync=  -D_Cilk_for=for -D_Cilk_spawn=  -D_Cilk_sync= --opencilk-resource-dir=../../opencilk/cheetah/build/"
REPORT_CFLAGS="-Rpass=.* -Rpass-analysis=.*"

CILKSAN_LIB=$TAPIR_LIB
CILKSAN_CFLAGS="-g -fsanitize=cilk"
CILKSAN_LDFLAGS="-fsanitize=cilk"

CILKSCALE_CFLAGS="-flto -fcsi"
CILKSCALE_LDFLAGS="-flto -fuse-ld=gold -L$TAPIR_LIB"
CILKSCALE_LDLIBS="-lclang_rt.cilkscale-x86_64"

#JEMALLOC_LDLIBS="-L`jemalloc-config --libdir` -Wl,-rpath,`jemalloc-config --libdir` -ljemalloc `jemalloc-config --libs`"

C_COMPILER() {
    case $1 in
	"tapir") echo "$TAPIR_CC $TAPIR_CILK_FLAG";;
	"ref") echo "$REF_PATH/clang $REF_CILK_FLAG";;
	"stapir") echo "$TAPIR_CC $TAPIR_CILK_FLAG $SERIAL_CFLAGS";;
	"sref") echo "$REF_PATH/clang $REF_CILK_FLAG $SERIAL_CFLAGS";;
	"serial") echo "$TAPIR_CC $SERIAL_CFLAGS";;
	"lazyd2") echo "$TAPIR_CC $LAZYD2_CILK_FLAG";;
	"lazyd0") echo "$TAPIR_CC $LAZYD0_CILK_FLAG";;
	"uipifork") echo "$TAPIR_CC $UIPI_CILK_FLAG";;
	"sigusrfork") echo "$TAPIR_CC $SIGUSR_CILK_FLAG";;
	"nopoll") echo "$TAPIR_CC $NOPOLL_CILK_FLAG";;
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
	"lazyd2") echo "$TAPIR_CXX $LAZYD2_CILK_FLAG";;
	"lazyd0") echo "$TAPIR_CXX $LAZYD0_CILK_FLAG";;
	"uipifork") echo "$TAPIR_CXX $UIPI_CILK_FLAG";;
	"sigusrfork") echo "$TAPIR_CXX $SIGUSR_CILK_FLAG";;
	"nopoll") echo "$TAPIR_CXX $NOPOLL_CILK_FLAG";;
	"gcc") echo "g++ $GCC_CILK_FLAG";;
	"sgcc") echo "g++ $GCC_CILK_FLAG $SERIAL_CFLAGS";;
	*) echo "Unknown compiler $1"; exit 1;;
    esac
}

RUN_ON_P_WORKERS() {
    P=$1
    echo "CILK_NWORKERS=$P $2"
    CILK_NWORKERS=$P $2
}
