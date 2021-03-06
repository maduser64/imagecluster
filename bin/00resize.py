#!/usr/bin/python3

"""
Python 3 
--------

Only python3 has (finally!) a decent multiprocessing module, which
handles KeyboardInterrupt (CTRL-C) *at all* and does this without need for
any extra hassle and awkward try..except stunts. Thank you!

verbose
-------

Use -v to know which image is processed. With multiprocessing, the order is
messed up a bit but you will still get a rough estimate of how many images are
left, assuming all images are equal in size and thus all processes are
approximately equally fast.

multiprocessing vs. threads
---------------------------

We use Python's multiprocessing instead of the default imagemagick OpenMP
parallelization since the former is a little faster -- and well .. coding and
benchmarking is fun!.

wall clock times, dual-core box, using 
  export OMP_NUM_THREADS=<max OpenMP threads>

    multiprocessing, ncore = 1,2,4, max OpenMP threads = 1

    $ for x in 1 2 4; do time ./00resize.py -n $x 0.2 files/*; done
    
    real    1m15.663s     # 1
    real    0m38.577s     # 2  ***
    real    0m39.365s     # 4
    
    multiprocessing, ncore = 1,2,4, max OpenMP threads = 2
    
    $ for x in 1 2 4; do time ./00resize.py -n $x 0.2 files/*; done
    
    real    0m46.304s     # 1  ***
    real    0m38.766s     # 2
    real    0m38.984s     # 4

The figures to compare are marked with ***, i.e. 2 threads vs. 2 processes
with 1 thread / core. With the latter, we are about factor 1.2 faster.

Note: We know that even setting OMP_NUM_THREADS=1 (which is probably
equivalent to "-limit threads 1" in the imagemagick case) is not a good idea
since there is still overhead caused by the creation of an OpenMP thread. The
only way to get rid of OpenMP completely is to re-compile imagemagick with
./configure --disable-openmp .

resize
------
"convert -resize" does some form of interpolation. The fastest resize (we only make
the image smaller) is "convert -sample": simply delete rows and columns
or, on other words *sample* only every Nth row and Mth column. This is 3x
faster than "-resize". It introduces some aliasing artifacts, but we usually
don't care as long as the main features are intact since we squash the image
down to smth like 8x8 later anyway.
"""

import os, multiprocessing, subprocess, functools, argparse
from imgcmp import cli, env

def _worker(tup, fraction=None, tgtdir=None, nfiles=None, verbose=False):
    idx, _src = tup
    src = os.path.abspath(_src)
    # /home/foo -> _home_foo -> home_foo
    tgt = os.path.join(tgtdir, src.replace('/','_')[1:])
    # -auto-orient: keep EXIF orientation information
    cmd = "convert -limit thread 1 -sample {}% -auto-orient {} {}".format(
            fraction*100, src, tgt)
    if verbose >= 1:   
        print("{} of {}".format(idx+1, nfiles))
    if verbose >= 2:
        print(cmd)
    if not os.path.exists(tgt):
        subprocess.call(cmd, shell=True)

if __name__ == '__main__':
    
    desc = """
Resize images to FRACTION*100 % with imagemagick's convert. Store them in dir TGTDIR
with their full name with / replaced by _, such that /path/to/file.png becomes
TGTDIR/path_to_file.png
"""
    parser = argparse.ArgumentParser(description=desc) 
    parser.add_argument('fraction', metavar='FRACTION', type=float,
                        help=r'fraction value for resizing (0..1), e.g. 0.25 '
                             r'for 25 percent')
    parser.add_argument('files', metavar='FILE', nargs='+',
                        help='image file names')
    parser.add_argument('-t', '--tgtdir',
                        default=cli.convert_dr,
                        help='store resized files here [%(default)s]')
    parser.add_argument('-n', '--ncore',
                        default=multiprocessing.cpu_count(), type=int,
                        help='number of cores for parallel work [%(default)s]')
    parser.add_argument('-v', '--verbose', default=0, action='count',
                        help='increase verbosity level, -vv prints convert commands')
    args = parser.parse_args()
    worker = functools.partial(_worker, 
                               fraction=args.fraction,
                               tgtdir=args.tgtdir,
                               nfiles=len(args.files),
                               verbose=args.verbose)
    pool = multiprocessing.Pool(args.ncore)
    pool.map(worker, enumerate(args.files))

