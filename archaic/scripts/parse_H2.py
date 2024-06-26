
import argparse
import numpy as np
import time
from archaic import masks
from archaic import one_locus
from archaic import two_locus
from archaic import utils
from archaic import parsing


def get_args():
    # get args
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--vcf_fname", required=True)
    parser.add_argument("-m", "--mask_fname", required=True)
    parser.add_argument("-r", "--map_fname", required=True)
    parser.add_argument("-o", "--out_fname", required=True)
    parser.add_argument("-w", "--window")
    parser.add_argument("-W", "--window_fname", default=None)
    parser.add_argument("-b", "--r_bins")
    parser.add_argument("-B", "--r_bin_fname", default=None)
    parser.add_argument("-bp", "--bp_thresh", type=int, default=0)
    return parser.parse_args()


def main():
    #
    args = get_args()
    if args.window:
        windows = np.array(eval(args.window))
    elif args.window_fname:
        windows = np.loadtxt(args.window_fname)
    else:
        print("using single window")
        windows = np.array([[0, np.inf]])
    if windows.ndim != 2:
        raise ValueError(f"windows must be dim2, but are dim{windows.ndim}")
    ###
    if windows.shape[1] == 3:
        bounds = windows[:, 2]
        windows = windows[:, :2]
    else:
        bounds = np.repeat(windows[-1, 1], len(windows))
    ###
    if args.r_bins:
        r_bins = np.array(eval(args.r_bins))
    elif args.r_bin_fname:
        r_bins = np.loadtxt(args.r_bin_fname)
    else:
        print("using default r bins")
        r_bins = np.logspace(-6, -2, 17)
    parsing.parse_H2(
        args.mask_fname,
        args.vcf_fname,
        args.map_fname,
        windows,
        bounds,
        r_bins,
        args.out_fname,
    )
    return 0


if __name__ == "__main__":
    main()
