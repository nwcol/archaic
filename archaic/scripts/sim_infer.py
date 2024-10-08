"""
fits models to simulated data using H2, H2+H, SFS, and composite methods
"""
import argparse
import demes
import msprime
import numpy as np

from archaic import inference, masks, two_locus, util
from archaic.parsing import parse_H2, bootstrap_H2, parse_SFS
from archaic.spectra import H2Spectrum


data_dir = 'data'
graph_dir = 'graphs'

needs_H2 = ['H2', 'H2H', 'composite']
needs_SFS = ['SFS', 'composite']


def get_args():
    # get args
    parser = argparse.ArgumentParser()
    parser.add_argument('-g', '--graph_fname', required=True)
    parser.add_argument('-p', '--options_fname', required=True)
    parser.add_argument('-o', '--out_prefix', required=True)
    parser.add_argument('-n', '--n_windows', type=int, default=100)
    parser.add_argument('-L', '--L', type=float, default=1e7)
    parser.add_argument('-s', '--samples', nargs='*', default=None)
    parser.add_argument('-u', '--u', type=float, default=1.35e-8)
    parser.add_argument('-r', '--r', type=float, default=1e-8)
    parser.add_argument('--infer_u', type=int, default=0)
    parser.add_argument('--max_iter', type=int, default=500)
    parser.add_argument('--method', default='Powell')
    parser.add_argument('-v', '--verbosity', type=int, default=1)
    parser.add_argument('--n_reps', type=int, default=100)
    parser.add_argument('--return_best', type=int, default=1)
    parser.add_argument(
        '--fit', nargs='*', default=['H2', 'H2H', 'SFS', 'composite']
    )
    parser.add_argument('--cluster_id', default='0')
    parser.add_argument('--process_id', default='0')
    return parser.parse_args()


def write_mask_file(L):
    #
    regions = np.array([[0, L]], dtype=np.int64)
    mask_fname = f'{data_dir}/mask{int(L / 1e6)}Mb.bed'
    chrom_num = 'chr0'
    masks.write_regions(regions, mask_fname, chrom_num)
    return mask_fname


def write_map_file(L, r):
    #
    cM = two_locus.map_function(r) * L
    map_fname = f'{data_dir}/map{int(L / 1e6)}Mb.txt'
    with open(map_fname, 'w') as file:
        file.write('Position(bp)\tRate(cM/Mb)\tMap(cM)\n')
        file.write('1\t0\t0\n')
        file.write(f'{int(L)}\t0\t{cM}')
    return map_fname


def coalsim(
    graph_fname,
    out_fname,
    samples,
    L,
    n=1,
    r=1e-8,
    u=None,
    contig_id='0'
):
    # perform a coalescent simulation using msprime.sim_ancestry
    def increment1(x):
        return [_ + 1 for _ in x]
    demography = msprime.Demography.from_demes(demes.load(graph_fname))
    config = {s: n for s in samples}
    ts = msprime.sim_ancestry(
        samples=config,
        ploidy=2,
        demography=demography,
        sequence_length=L,
        recombination_rate=r,
        discrete_genome=True
    )
    mts = msprime.sim_mutations(ts, rate=u)
    with open(out_fname, 'w') as file:
        mts.write_vcf(
            file,
            individual_names=samples,
            contig_id=str(contig_id),
            position_transform=increment1
        )
    print(
        util.get_time(),
        f'{int(L)} sites simulated and saved at {out_fname}'
    )
    return 0


def get_best_fit_graphs(graph_fnames, percentile):
    # return list of highest-LL graphs
    graphs = [demes.load(fname) for fname in graph_fnames]
    LLs = [float(graph.metadata['opt_info']['fopt']) for graph in graphs]
    threshold = np.quantile(LLs, percentile, method='linear')
    print(f'LL {percentile}th percentile: {threshold}')
    idx = np.nonzero(LLs > threshold)[0]
    for i in idx:
        print(f'{graph_fnames[i]}: LL = {LLs[i]}')
    return idx, [graph_fnames[i] for i in idx]


def main():
    #
    args = get_args()

    # make sure we have fit arguments
    if len(args.fit) == 0:
        raise ValueError('you must provide at least one fit argument!')

    graph = demes.load(args.graph_fname)
    if args.samples:
        sample_ids = args.samples
    else:
        sample_ids = [d.name for d in graph.demes if d.end_time == 0]
    tag = f'{args.out_prefix}_{args.cluster_id}_{args.process_id}'

    mask_fname = write_mask_file(args.L)
    map_fname = write_map_file(args.L, args.r)
    windows = np.array([[0, args.L]])
    bounds = np.array([args.L])
    r_bins = np.logspace(-6, -2, 17)

    # simulate and parse statistics
    vcf_fnames = []
    for i in range(args.n_windows):
        vcf_fname = f'{data_dir}/win{i}.vcf'
        vcf_fnames.append(vcf_fname)
        coalsim(
            args.graph_fname,
            vcf_fname,
            sample_ids,
            args.L,
            r=args.r,
            u=args.u
        )

    # declare these here for neatness
    H2_data_fname = f'{tag}_H2.npz'
    SFS_data_fname = f'{tag}_SFS.npz'

    # check whether we need H2
    want_H2 = False
    for stat in args.fit:
        if stat in needs_H2:
            want_H2 = True

    if want_H2:
        H2_dicts = []
        for i in range(args.n_windows):
            H2_dicts.append(
                parse_H2(
                    mask_fname,
                    vcf_fnames[i],
                    map_fname,
                    windows=windows,
                    bounds=bounds,
                    r_bins=r_bins
                )
            )
        H2_stats = bootstrap_H2(H2_dicts)
        np.savez(H2_data_fname, **H2_stats)
        H2_data = H2Spectrum.from_bootstrap_file(H2_data_fname, graph=graph)
    else:
        H2_data = None

    # check whether SFS is needed
    want_SFS = False
    for stat in args.fit:
        if stat in needs_SFS:
            want_SFS = True

    if want_SFS:
        parse_SFS(
            [mask_fname] * args.n_windows,
            vcf_fnames,
            SFS_data_fname,
            ref_as_ancestral=True
        )
        SFS_data, L = inference.read_SFS(SFS_data_fname, sample_ids)
    else:
        SFS_data = None

    # do we want to infer u?
    if args.infer_u:
        inf_u = None
        uL = None
    else:
        inf_u = args.u
        if want_SFS:
            uL = args.u * L

    # perturb the initial graph to get starting points
    inits = []
    for i in range(args.n_reps):
        fname = f'{graph_dir}/{tag}_init_rep{i}.yaml'
        inference.perturb_graph(
            args.graph_fname, args.options_fname, out_fname=fname
        )
        inits.append(fname)

    fits = {stat: [] for stat in args.fit}
    for i in range(args.n_reps):
        if 'H2' in fits:
            H2_fname = f'{graph_dir}/{tag}_H2_rep{i}.yaml'
            inference.fit_H2(
                inits[i],
                args.options_fname,
                H2_data,
                max_iter=args.max_iter,
                method=args.method,
                u=inf_u,
                verbosity=args.verbosity,
                use_H=False,
                out_fname=H2_fname
            )
            fits['H2'].append(H2_fname)

        if 'H2H' in fits:
            H2H_fname = f'{graph_dir}/{tag}_H2H_rep{i}.yaml'
            inference.fit_H2(
                inits[i],
                args.options_fname,
                H2_data,
                max_iter=args.max_iter,
                method=args.method,
                u=inf_u,
                verbosity=args.verbosity,
                use_H=True,
                out_fname=H2H_fname
            )
            fits['H2H'].append(H2H_fname)

        if 'SFS' in fits:
            SFS_fname = f'{graph_dir}/{tag}_SFS_rep{i}.yaml'
            inference.fit_SFS(
                inits[i],
                args.options_fname,
                SFS_data,
                uL=uL,
                L=L,
                max_iter=args.max_iter,
                method=args.method,
                verbosity=args.verbosity,
                out_fname=SFS_fname
            )
            fits['SFS'].append(SFS_fname)

        if 'composite' in fits:
            composite_fname = f'{graph_dir}/{tag}_composite_rep{i}.yaml'
            inference.fit_composite(
                inits[i],
                args.options_fname,
                H2_data,
                SFS_data,
                max_iter=args.max_iter,
                method=args.method,
                u=inf_u,
                L=L,
                verbosity=args.verbosity,
                out_fname=composite_fname
            )
            fits['composite'].append(composite_fname)

    percentile = 1 - args.return_best / args.n_reps
    print(f'returning {percentile * 100}% highest-ll graphs')

    for stat in fits:
        _, best_fits = get_best_fit_graphs(fits[stat], percentile)
        print(stat, best_fits)
        for fname in best_fits:
            base_name = fname.split('/')[-1]
            g = demes.load(fname)
            demes.dump(g, base_name)
    return 0


if __name__ == '__main__':
    main()
