

import numpy as np
import scipy


def multivariate_normal(mu, Sigma, x):
    """
    Evaluate a multivariate normal PDF with locations mu, covariances Sigma
    at x.

    :param mu:
    :param Sigma:
    :param x:
    :return:
    """
    k = len(mu)
    d = (
        ((2 * np.pi) ** k * np.linalg.det(Sigma)) ** -0.5
        * np.exp(-0.5 * (x - mu) @ np.linalg.inv(Sigma) @ (x - mu))
    )
    return d


def unscaled_multivariate_normal(mu, Sigma, x):
    """
    Evaluate a multivariate normal probability measure but do not scale it to
    be a pdf
    
    :param mu: 
    :param Sigma: 
    :param x: 
    :return: 
    """
    k = len(mu)
    d = np.exp(-0.5 * (x - mu) @ np.linalg.inv(Sigma) @ (x - mu))
    return d


def compound_lik(mu_dict, Sigma_dict, x_dict):

    # check to make sure dicts all have the same keys?
    liks = np.zeros(len(x_dict))
    for i, key in enumerate(x_dict):
        d = unscaled_multivariate_normal(
            mu_dict[key], Sigma_dict[key], x_dict[key]
        )
        liks[i] = - np.log(d)
    lik = liks.sum()
    return lik







































"""

Usage: python {yaml name} {first sampled population} {second sampled population}

For example: python one_pop.yaml X X


install with
pip install git+https://github.com/MomentsLD/moments.git@devel




import sys
import moments
import demes
import matplotlib.pylab as plt





graph = sys.argv[1]
X = sys.argv[2]
Y = sys.argv[3]



g = demes.load(graph)



if X == Y:
    sampled_demes = [X]
    sample_times = [0]

else:
    sample_demes = [X, Y]
    sample_times = [0, 0]



r = [0, 1e-7, 1e-6, 1e-5, 1e-4, 1e-3, 1e-2, 1e-1]  # you'll set these as your bin edges

u = 1.5e-8

Ne = 10000



y = moments.LD.LDstats.from_demes(

    g, sampled_demes=sampled_demes, sample_times=sample_times, u=u, r=r, Ne=Ne

)



H2_X = y.H2(X, phased=True)

H2_Y = y.H2(Y, phased=True)

H2_XY = y.H2(X, Y, phased=False)



# these values are for the bin edges, not bin midpoint - but we can average...

H2_X = (H2_X[:-1] + H2_X[1:]) / 2

H2_Y = (H2_Y[:-1] + H2_Y[1:]) / 2

H2_XY = (H2_XY[:-1] + H2_XY[1:]) / 2



r_mids = [(r[i] + r[i + 1]) / 2 for i in range(len(r) - 1)]



fig = plt.figure(1)

ax = plt.subplot(1, 1, 1)

ax.plot(r_mids, H2_X, label="X")

ax.plot(r_mids, H2_Y, label="Y")

ax.plot(r_mids, H2_XY, label="XY")

ax.set_xscale("log")

ax.legend()

ax.set_xlabel("r")

ax.set_ylabel("H2")

fig.tight_layout()

plt.show()"""