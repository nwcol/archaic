"""
Plot arbitrarily many H2-statistic .npz archives alongside arbitrarily many
expected H2 curves from graphs.

The usage
    python plot_H2.py -g [graph filename] -o [output filename]
plots expected H2 curves for demes that exist at time 0 in a demes graph

    python plot_H2.py -g [graph filename] -s [id1] ... -o [output filename]
plots expected H2 curves for the named samples

    python plot_H2.py -g [graph filename] -d [stat filename] \
     -o [output filename]
plots model expectations alongside empirical values. if more than one
statistic archives are plotted, the log-likelihoods in the legend are computed
using the first one.
"""
import argparse
import demes
import matplotlib.pyplot as plt
from matplotlib import cm
import numpy as np

from archaic import inference, plotting
from archaic.spectra import H2Spectrum


def get_args():
    # get args
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data_fnames', nargs='*', default=[])
    parser.add_argument('-g', '--graph_fnames', nargs='*', default=[])
    parser.add_argument("-o", "--out_fname", required=True)
    parser.add_argument("-u", "--u", type=float, default=1.35e-8)
    parser.add_argument('--alpha', type=float, default=0.05)
    parser.add_argument('--sample_ids', nargs='*', default=[])
    parser.add_argument('--title', default=None)
    parser.add_argument("--n_cols", type=int, default=5)
    parser.add_argument('--labels', nargs='*', default=None)
    parser.add_argument('--log_scale', type=int, default=0)
    parser.add_argument('--plot_H', type=int, default=1)
    return parser.parse_args()


def main():
    # if graphs are provided, only demes which occur in the first graph are
    # loaded from the data file.
    # conversely, if data and graphs are provided, the first data file is used
    # to compute likelihoods
    args = get_args()

    spectra = []
    labels = []
    n_datas = 0
    n_graphs = 0

    if args.sample_ids:
        sample_ids = args.sample_ids
        graph = None
    elif len(args.graph_fnames) > 0:
        sample_ids = None
        graph = demes.load(args.graph_fnames[0])
    else:
        sample_ids = None
        graph = None

    for fname in args.data_fnames:
        spectrum = H2Spectrum.from_bootstrap_file(
            fname,
            sample_ids=sample_ids,
            graph=graph
        )
        if not args.plot_H and spectrum.has_H:
            spectrum = spectrum.remove_H()
        spectra.append(spectrum)
        labels.append(fname.split('/')[-1])
        n_datas += 1

    # used to compute graph H2 values
    if sample_ids:
        _sample_ids = sample_ids
    elif len(args.data_fnames) > 0:
        _sample_ids = spectra[0].sample_ids
    else:
        # no data
        graph = demes.load(args.graph_fnames[0])
        _sample_ids = [d.name for d in graph.demes if d.end_time == 0]

    # getting r
    if len(args.data_fnames) > 0:
        r_bins = spectra[0].r_bins
        r = H2Spectrum.get_r(r_bins)
    else:
        r_bins = np.logspace(-6, -2, 17)
        r = H2Spectrum.get_r(r_bins)

    for graph_fname in args.graph_fnames:
        graph = demes.load(graph_fname)
        spectrum = H2Spectrum.from_graph(
            graph, _sample_ids, r, args.u, r_bins=r_bins
        )
        if len(args.data_fnames) > 0:
            ll = inference.get_ll(spectrum, spectra[0])
            ll_label = f', ll={np.round(ll, 0)}'
        else:
            ll_label = ''
        spectra.append(spectrum)
        basename = graph_fname.split('/')[-1]
        labels.append(f'{basename}{ll_label}')
        n_graphs += 1

    data_colors = ['b', 'orange', 'g', 'r', 'purple', 'brown', 'm', 'g']
    colors = data_colors[:n_datas] \
        + list(cm.gnuplot(np.linspace(0, 0.9, n_graphs)))

    fig, axs = plotting.plot_H2_spectra(
        *spectra,
        plot_H=args.plot_H,
        colors=colors,
        labels=labels,
        n_cols=args.n_cols,
        alpha=args.alpha,
        log_scale=args.log_scale
    )

    if args.title:
        fig.suptitle(args.title)
    plt.savefig(args.out_fname, dpi=200, bbox_inches='tight')
    return 0


if __name__ == "__main__":
    main()
