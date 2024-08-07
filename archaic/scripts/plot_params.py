"""
Plots parameter distributions
"""
import argparse
import matplotlib.pyplot as plt
import moments.Demes.Inference as minf
import numpy as np

from archaic import inference
from archaic import plotting


def get_args():
    # get args
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--params_fname", required=True)
    parser.add_argument("-g", "--graph_fname", default=None)
    parser.add_argument("-g1", "--g1", nargs='*', default=[])
    parser.add_argument("-g2", "--g2", nargs='*', default=[])
    parser.add_argument("-g3", "--g3", nargs='*', default=[])
    parser.add_argument("-g4", "--g4", nargs='*', default=[])
    parser.add_argument('--labels', nargs='*', default=None)
    parser.add_argument('--title', default=None)
    parser.add_argument('--marker_size', type=int, default=8)
    parser.add_argument('--n_cols', type=int, default=5)
    parser.add_argument("-o", "--out_fname", required=True)
    return parser.parse_args()


def parse_params(graph_fname, params_fname):
    # grab
    builder = minf._get_demes_dict(graph_fname)
    pars = minf._get_params_dict(params_fname)
    names, init, lower, upper = minf._set_up_params_and_bounds(pars, builder)
    return names, init, lower, upper


def plot():
    #
    args = get_args()
    if args.graph_fname is None:
        fname0 = args.g1[1]
        param_names, _, lower, upper = parse_params(
            fname0, args.params_fname
        )
        real_vals = None
    else:
        param_names, real_vals, lower, upper = parse_params(
            args.graph_fname, args.params_fname
        )
    bounds = np.array([lower, upper]).T
    arrs = []
    file_groups = [x for x in [args.g1, args.g2, args.g3, args.g4] if len(x) > 0]
    for fnames in file_groups:
        if len(fnames) > 0:
            _, arr = inference.get_param_arr(
                fnames, args.params_fname, permissive=True
            )
            arrs.append(arr)
    if args.labels is None:
        labels = [_fnames[0] for _fnames in file_groups]
        print(labels)
    else:
        labels = args.labels
    if len(labels) != len(arrs):
        raise ValueError('label length mismatches graph category length')
    plotting.plot_parameters(
        param_names,
        real_vals,
        bounds,
        labels,
        *arrs,
        marker_size=args.marker_size,
        title=args.title,
        n_cols=args.n_cols
    )
    plt.savefig(args.out_fname, dpi=200, bbox_inches='tight')


def main():
    #
    plot()
    return 0


if __name__ == "__main__":
    main()
