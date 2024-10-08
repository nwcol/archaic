"""
functions for fitting models to H2 and SFS statistics
"""
import demes
import numpy as np
import moments
import scipy

from archaic import util
from archaic.spectra import H2Spectrum


"""
handling graphs and options/parameters
"""


def perturb_graph(graph_fname, options_fname, out_fname=None, timeout=1000):
    # uniformly and randomly pick parameter values

    def log_uniform(lower, upper):
        # sample parameters log-uniformly
        log_lower = np.log10(lower)
        log_upper = np.log10(upper)
        log_draws = np.random.uniform(log_lower, log_upper)
        draws = 10 ** log_draws
        return draws

    builder = moments.Demes.Inference._get_demes_dict(graph_fname)
    options = moments.Demes.Inference._get_params_dict(options_fname)
    pnames, p0, lower_bounds, upper_bounds = \
        moments.Demes.Inference._set_up_params_and_bounds(options, builder)
    constraints = moments.Demes.Inference._set_up_constraints(options, pnames)
    if np.any(np.isinf(upper_bounds)):
        raise ValueError("all upper bounds must be specified!")
    above1 = np.where(lower_bounds >= 1)[0]
    below1 = np.where(lower_bounds < 1)[0]
    satisfied = False
    p = None
    i = 0

    while not satisfied:
        p = np.zeros(len(p0))
        p[above1] = np.random.uniform(
            lower_bounds[above1], upper_bounds[above1]
        )
        p[below1] = log_uniform(
            lower_bounds[below1], upper_bounds[below1]
        )
        if constraints:
            if np.all(constraints(p) > 0):
                satisfied = True
                print(p)
            else:
                i += 1
                if i > timeout:
                    raise ValueError('parameter perturbation timeout!')
        else:
            satisfied = True

    builder = moments.Demes.Inference._update_builder(builder, options, p)
    graph = demes.Graph.fromdict(builder)
    if out_fname is not None:
        demes.dump(graph, out_fname)
    else:
        return out_fname


def get_param_arr(graph_fnames, options_fname, permissive=False):
    # load a bunch of parameters from many graph files at once
    # shape (n_files, n_parameters)
    params = moments.Demes.Inference._get_params_dict(options_fname)
    if permissive:
        for i in range(len(params['parameters'])):
            params['parameters'][i]['lower_bound'] *= 0.99
            params['parameters'][i]['upper_bound'] *= 1.01
    names = None
    arr = []
    for fname in graph_fnames:
        g = moments.Demes.Inference._get_demes_dict(fname)
        names, vals, _, __, = \
            moments.Demes.Inference._set_up_params_and_bounds(params, g)
        arr.append(vals)
    return names, np.array(arr)


"""
optimization functions
"""


_out_of_bounds = -1e10
_n_func_calls = 0
_n_iters = 0


_init_u = 1.35e-8
_lower_u = 1e-8
_upper_u = 1.6e-8


def fit_H2(
    graph_fname,
    options_fname,
    data,
    max_iter=1000,
    method='NelderMead',
    u=None,
    verbosity=1,
    use_H=True,
    out_fname=None
):
    #
    if not use_H and data.has_H:
        data = data.remove_H()
    print(
        util.get_time(),
        f'fitting H2 to data for demes {data.sample_ids}'
    )
    builder = moments.Demes.Inference._get_demes_dict(graph_fname)
    options = moments.Demes.Inference._get_params_dict(options_fname)
    pnames, p0, lower_bounds, upper_bounds = \
        moments.Demes.Inference._set_up_params_and_bounds(options, builder)
    constraints = moments.Demes.Inference._set_up_constraints(options, pnames)

    if u is None:
        print(util.get_time(), f'fitting u as a free parameter')
        fit_u = True
        pnames = np.append(pnames, 'u')
        p0 = np.append(p0, _init_u)
        lower_bounds = np.append(lower_bounds, _lower_u)
        upper_bounds = np.append(upper_bounds, _upper_u)
    else:
        fit_u = False

    print_start(pnames, p0)

    args = (
        builder,
        options,
        data,
        u,
        lower_bounds,
        upper_bounds,
        constraints,
        verbosity,
        fit_u,
        use_H
    )
    ret = optimize(
        objective_H2,
        p0,
        args,
        u=u,
        builder=builder,
        options=options,
        method=method,
        max_iter=max_iter,
        out_fname=out_fname,
        bounds=(lower_bounds, upper_bounds),
        fit_u=fit_u
    )
    return ret


def objective_H2(
    p,
    builder,
    options,
    data,
    u,
    lower_bounds=None,
    upper_bounds=None,
    constraints=None,
    verbosity=1,
    fit_u=False,
    use_H=True
):
    #
    global _n_func_calls
    _n_func_calls += 1

    if fit_u:
        u = p[-1]

    if check_params(p, lower_bounds, upper_bounds, constraints) != 0:
        return -_out_of_bounds

    builder = moments.Demes.Inference._update_builder(builder, options, p)
    graph = demes.Graph.fromdict(builder)
    model = H2Spectrum.from_graph(
        graph, data.sample_ids, data.r, u, get_H=use_H
    )
    ll = get_ll(model, data)

    if verbosity > 0 and _n_func_calls % verbosity == 0:
        print_status(_n_func_calls, ll, p)
    return -ll


def fit_SFS(
    graph_fname,
    options_fname,
    data,
    uL=None,
    L=None,
    max_iter=1000,
    method='NelderMead',
    verbosity=1,
    out_fname=None
):
    #
    print(
        util.get_time(),
        f'fitting SFS to data for demes {data.pop_ids}'
    )
    builder = moments.Demes.Inference._get_demes_dict(graph_fname)
    options = moments.Demes.Inference._get_params_dict(options_fname)
    pnames, p0, lower_bounds, upper_bounds = \
        moments.Demes.Inference._set_up_params_and_bounds(options, builder)
    constraints = moments.Demes.Inference._set_up_constraints(options, pnames)

    if uL is None:
        if L is None:
            raise ValueError('if you do not provide uL, you must provide L!')
        else:
            print(util.get_time(), f'fitting u as a free parameter')
            fit_u = True
            pnames = np.append(pnames, 'u')
            p0 = np.append(p0, _init_u)
            lower_bounds = np.append(lower_bounds, _lower_u)
            upper_bounds = np.append(upper_bounds, _upper_u)
    else:
        fit_u = False

    print_start(pnames, p0)

    args = (
        builder,
        options,
        data,
        uL,
        L,
        lower_bounds,
        upper_bounds,
        constraints,
        verbosity,
        fit_u
    )
    ret = optimize(
        objective_SFS,
        p0,
        args,
        builder=builder,
        options=options,
        method=method,
        max_iter=max_iter,
        out_fname=out_fname,
        bounds=(lower_bounds, upper_bounds)
    )
    return ret


def objective_SFS(
    p,
    builder,
    options,
    data,
    uL,
    L=None,
    lower_bounds=None,
    upper_bounds=None,
    constraints=None,
    verbosity=1,
    fit_u=False
):
    #
    global _n_func_calls
    _n_func_calls += 1

    if check_params(p, lower_bounds, upper_bounds, constraints) != 0:
        return -_out_of_bounds

    if fit_u:
        u = p[-1]
        uL = L * u

    builder = moments.Demes.Inference._update_builder(builder, options, p)
    graph = demes.Graph.fromdict(builder)
    sampled_demes = data.pop_ids
    sample_sizes = data.sample_sizes
    end_times = {d.name: d.end_time for d in graph.demes}
    sample_times = [end_times[d] for d in sampled_demes]
    model = moments.Demes.SFS(
        graph,
        sampled_demes=sampled_demes,
        sample_sizes=sample_sizes,
        sample_times=sample_times,
        u=uL
    )
    ll = moments.Inference.ll(model, data)

    if verbosity > 0 and _n_func_calls % verbosity == 0:
        print_status(_n_func_calls, ll, p)
    return -ll


def fit_composite(
    graph_fname,
    options_fname,
    H2_data,
    SFS_data,
    max_iter=1000,
    method='NelderMead',
    L=None,
    u=None,
    verbosity=1,
    out_fname=None
):
    #
    if H2_data.has_H:
        H2_data = H2_data.remove_H()
    print(
        util.get_time(),
        f'fitting SFS and H2 to data for demes {H2_data.sample_ids}'
    )
    builder = moments.Demes.Inference._get_demes_dict(graph_fname)
    options = moments.Demes.Inference._get_params_dict(options_fname)
    pnames, p0, lower_bounds, upper_bounds = \
        moments.Demes.Inference._set_up_params_and_bounds(options, builder)
    constraints = moments.Demes.Inference._set_up_constraints(options, pnames)

    if L is None:
        raise ValueError('you must provide an L argument')
    if u is None:
        print(util.get_time(), f'fitting u as a free parameter')
        fit_u = True
        pnames = np.append(pnames, 'u')
        p0 = np.append(p0, _init_u)
        lower_bounds = np.append(lower_bounds, _lower_u)
        upper_bounds = np.append(upper_bounds, _upper_u)
    else:
        fit_u = False

    print_start(pnames, p0)

    args = (
        builder,
        options,
        H2_data,
        SFS_data,
        u,
        L,
        lower_bounds,
        upper_bounds,
        constraints,
        verbosity,
        fit_u
    )
    ret = optimize(
        objective_composite,
        p0,
        args,
        builder=builder,
        options=options,
        method=method,
        max_iter=max_iter,
        out_fname=out_fname,
        bounds=(lower_bounds, upper_bounds)
    )
    return ret


def objective_composite(
    p,
    builder,
    options,
    H2_data,
    SFS_data,
    u,
    L,
    lower_bounds=None,
    upper_bounds=None,
    constraints=None,
    verbosity=1,
    fit_u=False
):
    #
    global _n_func_calls
    _n_func_calls += 1

    if check_params(p, lower_bounds, upper_bounds, constraints) != 0:
        return -_out_of_bounds

    if fit_u:
        u = p[-1]
        uL = L * u

    builder = moments.Demes.Inference._update_builder(builder, options, p)
    graph = demes.Graph.fromdict(builder)
    # get expected SFS
    sampled_demes = SFS_data.pop_ids
    sample_sizes = SFS_data.sample_sizes
    end_times = {d.name: d.end_time for d in graph.demes}
    sample_times = [end_times[d] for d in sampled_demes]
    SFS_model = moments.Demes.SFS(
        graph,
        sampled_demes=sampled_demes,
        sample_sizes=sample_sizes,
        sample_times=sample_times,
        u=u * L
    )
    H2_model = H2Spectrum.from_graph(
        graph, H2_data.sample_ids, H2_data.r, u, get_H=False
    )
    ll = moments.Inference.ll(SFS_model, SFS_data) + get_ll(H2_model, H2_data)

    if verbosity > 0 and _n_func_calls % verbosity == 0:
        print_status(_n_func_calls, ll, p)
    return -ll


def check_params(p, lower_bounds, upper_bounds, constraints):
    #
    ret = 0
    if lower_bounds is not None and np.any(p < lower_bounds):
        ret = 1
    elif upper_bounds is not None and np.any(p > upper_bounds):
        ret = 1
    elif constraints is not None and np.any(constraints(p) <= 0):
        ret = 1
    return ret


def optimize(
    object_func,
    p0,
    args,
    u=None,
    builder=None,
    options=None,
    method='NelderMead',
    max_iter=1000,
    out_fname=None,
    bounds=None,
    fit_u=False
):
    """
    minimizes an objective function from initial parameters p0 using a tuple
    of args.

    when out_fname is provided, saves a graph at the specified path. otherwise
    returns a demes graph object. optimization exit status and some other
    information like the number of function calls are stored in a field called
    'opt_info' in the output demes graph/file.

    :param object_func: function that returns a negative log likelihood given
        p and args. data, a graph builder, options etc. are stored in args
    :param p0: vector of initial parameters
    :param args: tuple of arguments to object_func
    :param builder:
    :param options:
    :param method: (optional, default 'NelderMead'; specifies a scipy fmin
        function. options are 'NelderMead', 'Powell', 'BGFS', 'LBFGSB'
    :type method: string
    :param max_iter: (optional, default 1000) maximum number of scipy
        function iterations
    :param out_fname: (optional) name of output .yaml demes graph file
    :param bounds: (optional) only used for the LBFGSB algorithm. a tuple of
        arrays of the form (lower_bounds, upper_bounds)
    :param u:
    :param fit_u:
    :return:
    """
    methods = ['NelderMead', 'Powell', 'BFGS', 'LBFGSB']

    if method not in methods:
        raise ValueError(f'method: {method} is not in {methods}')

    if method == 'NelderMead':
        opt = scipy.optimize.fmin(
            object_func,
            p0,
            args=args,
            maxiter=max_iter,
            full_output=True
        )
        p = opt[0]
        fopt, n_iter, func_calls, flag = opt[1:5]

    elif method == 'BFGS':
        opt = scipy.optimize.fmin_bfgs(
            object_func,
            p0,
            args=args,
            maxiter=max_iter,
            full_output=True
        )
        p = opt[0]
        fopt, _, __, func_calls, grad_calls, flag = opt[1:7]
        # is it correct to equate these?
        n_iter = grad_calls

    elif method == 'LBFGSB':
        lower, upper = bounds
        _bounds = list(zip(lower, upper))
        opt = scipy.optimize.fmin_l_bfgs_b(
            object_func,
            p0,
            args=args,
            maxiter=max_iter,
            bounds=_bounds,
            epsilon=1e-2,
            pgtol=1e-5,
            approx_grad=True
        )
        p, fopt, d = opt
        n_iter = d['nit']
        func_calls = d['funcalls']
        flag = d['warnflag']

    elif method == 'Powell':
        opt = scipy.optimize.fmin_powell(
            object_func,
            p0,
            args=args,
            maxiter=max_iter,
            full_output=True,
        )
        p = opt[0]
        fopt, _, n_iter, func_calls, flag = opt[1:6]

    else:
        return 1

    global _n_func_calls
    print_status(_n_func_calls, 'fit p:', p)
    _n_func_calls = 0

    if fit_u:
        info_u = p[-1]
        p = p[:-1]
    else:
        info_u = u

    info = dict(
        method=method,
        objective_func=object_func.__name__,
        fopt=-fopt,
        max_iter=max_iter,
        n_iter=n_iter,
        func_calls=func_calls,
        flag=flag,
        u=info_u
    )

    print('\n'.join([f'{key}: {info[key]}' for key in info]))

    if builder is None or options is None:
        return p, info

    builder = moments.Demes.Inference._update_builder(builder, options, p)
    graph = demes.Graph.fromdict(builder)
    graph.metadata['opt_info'] = info

    if out_fname is not None:
        demes.dump(graph, out_fname)
    else:
        return graph



def print_start(pnames, p0):

    print_status(0, 'pnames', pnames)
    print_status(0, 'p0', p0)


def print_status(n_calls, ll, p):
    #
    t = util.get_time()
    _n = f'{n_calls:<6}'
    if isinstance(ll, float):
        _ll = f'{np.round(ll, 2):>10}'
    else:
        _ll = f'{ll:>10}'
    fmt_p = []
    for x in p:
        if isinstance(x, str):
            fmt_p.append(f'{x:>10}')
        else:
            if x > 1:
                fmt_p.append(f'{np.round(x, 1):>10}')
            else:
                sci = np.format_float_scientific(x, 2, trim='k')
                fmt_p.append(f'{sci:>10}')
    _p = ''.join(fmt_p)
    print(t, _n, _ll, _p)


_inv_cov_cache = {}


def log_gaussian(x, mu, inv_cov):

    return -(x - mu) @ inv_cov @ (x - mu)


def get_ll(model, data):
    # operates on H2Spectrum instances
    return get_bin_ll(model, data).sum()


def get_bin_ll(model, data):
    # operates on H2Spectrum instances
    xs = data.arr
    if data.covs is None:
        raise ValueError('data has no covariance matrix!')
    else:
        covs = data.covs
    mus = model.arr
    return _get_bin_ll(xs, mus, covs)


def _get_ll(xs, mus, covs):
    # operates on bare arrays
    return _get_bin_ll(xs, mus, covs).sum()


def _get_bin_ll(xs, mus, covs):
    # operates on bare arrays
    lens = np.array([len(xs), len(mus), len(covs)])
    if not np.all(lens == lens[0]):
        raise ValueError('xs, mus, covs lengths do not match')
    bin_ll = np.zeros(len(xs))
    for i in range(len(xs)):
        if i in _inv_cov_cache and np.all(_inv_cov_cache[i]['cov'] == covs[i]):
            inv_cov = _inv_cov_cache[i]['inv']
        else:
            inv_cov = np.linalg.inv(covs[i])
            _inv_cov_cache[i] = dict(cov=covs[i], inv=inv_cov)
        bin_ll[i] = log_gaussian(xs[i], mus[i], inv_cov)
    return bin_ll


"""
confidence intervals
"""


def get_uncerts(
    graph_fname,
    options_fname,
    data,
    bootstraps=None,
    u=None,
    delta=0.01,
    method='GIM'
):
    #
    builder = moments.Demes.Inference._get_demes_dict(graph_fname)
    options = moments.Demes.Inference._get_params_dict(options_fname)
    pnames, p0, lower_bound, upper_bound = \
        moments.Demes.Inference._set_up_params_and_bounds(options, builder)

    if u is None:
        # my temporary means of getting mutation rate into p0
        g = demes.load(graph_fname)
        _u = float(g.metadata['opt_info']['u'])
        pnames.append('u')
        p0 = np.append(p0, _u)
        fit_u = True
    else:
        fit_u = False

    def model_func(p):
        # takes parameters and returns expected statistics
        nonlocal builder
        nonlocal options
        nonlocal data
        nonlocal u
        nonlocal fit_u

        if fit_u:
            u = p[-1]

        builder = moments.Demes.Inference._update_builder(builder, options, p)
        graph = demes.Graph.fromdict(builder)
        model = H2Spectrum.from_graph(graph, data.sample_ids, data.r, u)
        return model

    if method == 'FIM':
        H = get_godambe_matrix(
            model_func,
            p0,
            data,
            bootstraps,
            delta,
            just_H=True
        )
        uncerts = np.sqrt(np.diag(np.linalg.inv(H)))

    elif method == 'GIM':
        if bootstraps is None:
            raise ValueError('You need bootstraps to use the GIM method!')
        godambe_matrix = get_godambe_matrix(
            model_func,
            p0,
            data,
            bootstraps,
            delta
        )
        uncerts = np.sqrt(np.diag(np.linalg.inv(godambe_matrix)))
    else:
        uncerts = None

    return pnames, p0, uncerts


_ll_cache = {}


def get_godambe_matrix(
    model_func,
    p0,
    data,
    bootstraps,
    delta,
    just_H=False
):
    """
    """

    def func(p, data):
        # compute log-likelihood given parameters, data
        # cache check
        key = tuple(p)
        if key in _ll_cache:
            model = _ll_cache[key]
        else:
            model = model_func(p)
            _ll_cache[key] = model
        return get_ll(model, data)

    H = -get_hessian(func, p0, data, delta)

    if just_H:
        return H

    J = np.zeros((len(p0), len(p0)))
    for i, bootstrap in enumerate(bootstraps):
        cU = get_gradient(func, p0, delta, bootstrap)
        cJ = cU @ cU.T
        J += cJ

    J = J / len(bootstraps)
    J_inv = np.linalg.inv(J)
    godambe_matrix = H @ J_inv @ H
    return godambe_matrix


def get_hessian(ll_func, p0, data, delta):
    #
    f0 = ll_func(p0, data)
    hs = delta * p0

    hessian = np.zeros((len(p0), len(p0)))

    for i in range(len(p0)):
        for j in range(i, len(p0)):
            _p = np.array(p0, copy=True, dtype=float)

            if i == j:
                _p[i] = p0[i] + hs[i]
                fp = ll_func(_p, data)
                _p[i] = p0[i] - hs[i]
                fm = ll_func(_p, data)

                element = (fp - 2 * f0 + fm) / hs[i] ** 2

            else:
                _p[i] = p0[i] + hs[i]
                _p[j] = p0[j] + hs[j]
                fpp = ll_func(_p, data)

                _p[i] = p0[i] + hs[i]
                _p[j] = p0[j] - hs[j]
                fpm = ll_func(_p, data)

                _p[i] = p0[i] - hs[i]
                _p[j] = p0[j] + hs[j]
                fmp = ll_func(_p, data)

                _p[i] = p0[i] - hs[i]
                _p[j] = p0[j] - hs[j]
                fmm = ll_func(_p, data)

                element = (fpp - fpm - fmp + fmm) / (4 * hs[i] * hs[j])

            hessian[i, j] = element
            hessian[j, i] = element

    return hessian


def get_gradient(func, p0, delta, args):
    #

    # should be changed to match moments version
    hs = delta * p0

    # column
    gradient = np.zeros((len(p0), 1))

    for i in range(len(p0)):
        _p = np.array(p0, copy=True, dtype=float)

        _p[i] = p0[i] + hs[i]
        fp = func(_p, args)

        _p[i] = p0[i] - hs[i]
        fm = func(_p, args)

        gradient[i] = (fp - fm) / (2 * hs[i])

    return gradient


"""
loading SFS from my .npz archives [subject to change]
"""


def read_SFS(fname, pop_ids=None, graph=None):
    #
    if pop_ids is None and graph is None:
        raise ValueError('you must provide pop_ids or graph!')
    file = np.load(fname)
    samples = file['samples']
    SFS = moments.Spectrum(
        file['SFS'],
        pop_ids=samples
    )
    if pop_ids is not None:
        pass
    elif graph is not None:
        deme_names = [d.name for d in graph.demes]
        pop_ids = [d for d in deme_names if d in samples]
    not_sampled = [i for i in range(len(samples)) if samples[i] not in pop_ids]
    _SFS = SFS.marginalize(not_sampled)
    return _SFS, file['n_sites']


"""
utilities for remote inference
"""


def get_tag(prefix, cluster, process):
    # get a string naming an output .yaml file
    c = p = ''
    if len(cluster) > 0:
        c = f'_{cluster}'
    if len(process) > 0:
        p = f'_{process}'
    tag = f'{prefix}{c}{p}'
    return tag


