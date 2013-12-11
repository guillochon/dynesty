# Licensed under a 3-clause BSD style license - see LICENSE
"""Simple implementation of nested sampling routine to evaluate Bayesian
evidence."""

import math
import time
from sys import stdout

import numpy as np
from scipy.cluster.vq import kmeans2

def randsphere(n):
    """Draw a random point within a n-dimensional unit sphere"""

    z = np.random.randn(n)
    return z * np.random.rand()**(1./n) / np.sqrt(np.sum(z**2))

def bounding_ellipsoid(x):
    """
    Calculate bounding ellipsoid containing all samples x.

    Parameters
    ----------
    x : (nobj, ndim) ndarray
        Coordinates of points.

    Returns
    -------
    scaled_cov : ndarray of shape (ndim, ndim)
        (f * C) which is the covariance of the data points, C,
        times an enlargement factor, f, that ensures that the ellipse
        defined by ``x^T <dot> (fC)^{-1} <dot> x <= 1`` encloses
        all points in the input set.
    vs : (ndim, ndim) ndarray
        Scaled eigenvectors (in columns): vs[:,i] is the i-th eigenvector.
    x_mean : (ndim,) ndarray
        Average coordinates of all samples.

    Notes
    -----
    To get the scaled eigenvectors::

        w, v = np.linalg.eig(scaled_cov)
        vs = np.dot(v, np.diag(np.sqrt(w)))  # scaled eigenvectors


    For the 2-d case, to verify that the generated ellipse encloses all
    the points, the ellipse can be plotted using matplotlib on an existing
    Axes  ``ax`` as follows::

        from matplotlib.patches import Ellipse

        # get scaled eigenvectors
        w, v = np.linalg.eig(scaled_cov)
        vs = np.dot(v, np.diag(np.sqrt(w)))  # scaled eigenvectors

        width = np.sqrt(np.sum(vs[:,1]**2)) * 2.
        height = np.sqrt(np.sum(vs[:,0]**2)) * 2.
        angle = math.atan(vs[1,1] / vs[0,1]) * 180./math.pi
        e = Ellipse(mean, width, height, angle)
        e.set_facecolor('None')
        ax.add_artist(e)

    To draw the vectors ``vs``:
    
        for i in [0,1]:
            plt.arrow(mean[0], mean[1], vs[0, i], vs[1, i])
    """

    x_mean = np.mean(x, axis=0)
    x_prime = x - x_mean
    cov = np.cov(x_prime, rowvar=0)
    
    # calculate expansion factor necessary to bound all the points
    factors = np.empty(len(x), dtype=np.float)
    cov_inv = np.linalg.inv(cov)
    for i in range(len(x)):
        factors[i] = np.dot(np.dot(x_prime[i,:], cov_inv), x_prime[i,:])
    f = np.sqrt(np.max(factors))

    return f * cov, x_mean

def ellipsoid_volume(scaled_cov):
    """
    Parameters
    ----------
    scaled_cov : (ndim, ndim) ndarray
        Scaled covariance matrix.

    Returns
    -------
    volume : float
    """
    vol = np.sqrt(np.det(scaled_cov))

    # proportionality constant depending on dimension
    ndim = len(scaled_cov)
    if ndim % 2 == 0:
        i = 2
        while i <= ndim:
            vol *= (2. / i * np.pi)
            i += 2
    else:
        vol *= 2.
        i = 3
        while i <= ndim:
            vol *= (2. / i * np.pi)
            i += 2

    return vol

def sample_ellipsoid(scaled_cov, x_mean, nsamples=1):
    """Chose sample(s) randomly distributed within an ellipsoid.
    
    Parameters
    ----------
    scaled_cov : (ndim, ndim) ndarray
        Scaled covariance matrix.
    x_mean : (ndim,) ndarray
        Simple average of all samples.

    Returns
    -------
    x : (nsamples, ndim) array, or (ndim,) array when nsamples == 1
        Coordinates within the ellipsoid.
    """

    # Get scaled eigenvectors (in columns): vs[:,i] is the i-th eigenvector.
    w, v = np.linalg.eig(scaled_cov)
    vs = np.dot(v, np.diag(np.sqrt(w)))

    ndim = len(x_mean)
    if nsamples == 1:
        return np.dot(vs, randsphere(ndim)) + x_mean

    x = np.empty((nsamples, ndim), dtype=np.float)
    for i in range(nsamples):
        x[i, :] = np.dot(vs, randsphere(ndim)) + x_mean
    return x

def bounding_ellipsoids(x, min_vol, ellipsoid=None, ellipsoid_vol=None):
    """Calculate a set of ellipses that bound the points.

    Parameters
    ----------
    x : (nobj, ndim) ndarray
        Coordinates of points.
    min_vol : float
        Minimum allowed volume of ellipses enclosing points.
    ellipsoid : (float, float), optional
        If known, the bounding ellipsoid of the points `x`. (If not supplied,
        it will be calculated.
    ellipsoid_vol : float, optional

    Returns
    -------
    ellipsoids : list of 2-tuples
        Ellipsoids, each represented by a tuple: ``(scaled_cov, x_mean)``
    """

    ellipses = []
    nobj, ndim = x.shape   

    # Calculate bounding ellipsoid for all the points, if not already known.
    if ellipsoid is None:
        ellipsoid = bounding_ellipsoid(x) 
        ellipsoid_vol = ellipsoid_volume(ellipsoid[0])

        # enlarge ellipse so that it has at least the minimum volume
        if ellipsoid_vol < min_vol:
            ellipsoid[0] *= (min_vol / ellipsoid_vol) ** (1./ndim)
            ellipsoid_vol = min_vol

    # Split points into two clusters using k-means clustering with k=2
    # centroid = (2, ndim) ; label = (nobj,)
    centroid, label = kmeans2(x, 2, iter=10)

    recalculate = True
    while recalculate:

        # calculate bounding ellipse of each set
        # (entries in `label` should be 0 or 1
        # corresponding to the cluster num)
        cluster_x = []
        cluster_ellipsoids = [] # 2-tuples of (scaled_cov, x_mean)
        for k in [0, 1]:            
            x_k = x[label == k, :] # points in this cluster
            n_k = len(x_k)
            cluster_ellipsoids = bounding_ellipsoid(x_k)  # ellipse around points
            evol_k = ellipsoid_volume(vs_k) # volume of ellipse

            # enlarge ellipse so that it is at least as large as the fractional
            # volume according to the number of points in the cluster
            min_vol_k = min_vol * n_k / nobj
            if evol_k < min_vol_k:
                vs_k *= (min_vol_k / evol_k) ** (1./ndim)

            # save ellipse and points
            cluster_X.append(X_k)
            cluster_ell.append((vs_k, mean_k))

        # reassign each point to the cluster that gives it the smallest h_k:
        #
        # h_k(point) = V_k(actual) / V_k(expected) * d_k(point)
        #
        # where
        #
        # V_k(actual) = volume of ellipsoid k
        # V_k(expected) = n_k / N * e^(-i/N)   <-- iteration i
        # d_k(point) = Mahalanobis distance

        # mahalanobis distance squared:
        # delta = u - v
        # m = np.dot(np.dot(delta, VI), delta)
        # 
        # where in this case, VI = (f * C)^-1

        # if (no points were reassigned):
        #     recalculate = False
   
    # if V(E_1) + V(E_2) < V(E) or V(E) > 2V(S):
    #     perform entire algorithm on each subset
    # Otherwise the Full ellipse E is good, return it.



def nest(loglikelihood, prior, npar, nobj=50, maxiter=10000,
         verbose=False, verbose_name=''):
    """Simple nested sampling algorithm to evaluate Bayesian evidence.

    Parameters
    ----------
    loglikelihood : func
        Function returning log(likelihood) given parameters as a 1-d numpy
        array of length `npar`. 
    prior : func
        Function translating a unit cube to the parameter space according to 
        the prior. The input is a 1-d numpy array with length `npar`, where
        each value is in the range [0, 1). The return value should also be a
        1-d numpy array with length `npar`, where each value is a parameter.
        The return value is passed to the loglikelihood function. For example,
        for a 2 parameter model with flat priors in the range [0, 2), the
        function would be

            def prior(u):
                return 2. * u

    npar : int
        Number of parameters.
    nobj : int, optional
        Number of random samples. Larger numbers result in a more finely
        sampled posterior (more accurate evidence), but also a larger
        number of iterations required to converge. Default is 50.
    maxiter : int, optional
        Maximum number of iterations. Iteration may stop earlier if
        termination condition is reached. Default is 10000. The total number
        of likelihood evaluations will be ``nexplore * niter``.
    verbose : bool, optional
        Print a single line of running total iterations.
    verbose_name : str, optional
        Print this string at start of the iteration line printed when
        verbose=True.

    Returns
    -------
    results : dict
        Containing following keys:

        * `niter` (int) number of iterations.
        * `ncalls` (int) number of likelihood calls.
        * `time` (float) time in seconds.
        * `logz` (float) log of evidence.
        * `logzerr` (float) error on `logz`.
        * `loglmax` (float) Maximum likelihood of any sample.
        * `h` (float) information.
        * `samples_parvals` (array, shape=(nsamples, npar)) parameter values
          of each sample.
        * `samples_wt` (array, shape=(nsamples,) Weight of each sample.

    Notes
    -----
    This is an implementation of John Skilling's Nested Sampling algorithm,
    following the ellipsoidal sampling algorithm in Shaw et al (2007). Only a
    single ellipsoid is used.
    
    Sample Weights are ``likelihood * prior_vol`` where
    prior_vol is the fraction of the prior volume the sample represents.

    References
    ----------
    http://www.inference.phy.cam.ac.uk/bayesys/
    Shaw, Bridges, Hobson 2007, MNRAS, 378, 1365
    """

    # Initialize objects and calculate likelihoods
    objects_u = np.random.random((nobj, npar)) #position in unit cube
    objects_v = np.empty((nobj, npar), dtype=np.float) #position in unit cube
    objects_logl = np.empty(nobj, dtype=np.float)  # log likelihood
    for i in range(nobj):
        objects_v[i,:] = prior(objects_u[i,:])
        objects_logl[i] = loglikelihood(objects_v[i,:])

    # Initialize values for nested sampling loop.
    samples_parvals = [] # stored objects for posterior results
    samples_logwt = []
    loglstar = None  # ln(Likelihood constraint)
    h = 0.  # Information, initially 0.
    logz = -1.e300  # ln(Evidence Z, initially 0)
    # ln(width in prior mass), outermost width is 1 - e^(-1/n)
    logwidth = math.log(1. - math.exp(-1./nobj))
    loglcalls = nobj #number of calls we already made

    # Nested sampling loop.
    ndecl = 0
    logwt_old = None
    time0 = time.time()
    for it in range(maxiter):
        if verbose:
            if logz > -1.e6:
                print "\r{} iter={:6d} logz={:8f}".format(verbose_name, it,
                                                          logz),
            else:
                print "\r{} iter={:6d} logz=".format(verbose_name, it),
            stdout.flush()

        # worst object in collection and its weight (= width * likelihood)
        worst = np.argmin(objects_logl)
        logwt = logwidth + objects_logl[worst]

        # update evidence Z and information h.
        logz_new = np.logaddexp(logz, logwt)
        h = (math.exp(logwt - logz_new) * objects_logl[worst] +
             math.exp(logz - logz_new) * (h + logz) -
             logz_new)
        logz = logz_new

        # Add worst object to samples.
        samples_parvals.append(np.array(objects_v[worst]))
        samples_logwt.append(logwt)

        # The new likelihood constraint is that of the worst object.
        loglstar = objects_logl[worst]

        # calculate the ellipsoid in parameter space that contains all the
        # samples (including the worst one).
        vs, mean = ellipsoid(objects_u, expand=1.06)

        # choose a point from within the ellipse until it has likelihood
        # better than loglstar
        while True:
            u = sample_ellipsoid(vs, mean)
            if np.any(u < 0.) or np.any(u > 1.):
                continue
            v = prior(u)
            logl = loglikelihood(v)
            loglcalls += 1

            # Accept if and only if within likelihood constraint.
            if logl > loglstar:
                objects_u[worst] = u
                objects_v[worst] = v
                objects_logl[worst] = logl
                break

        # Shrink interval
        logwidth -= 1./nobj

        # stop when the logwt has been declining for more than 10 or niter/4
        # consecutive iterations.
        if logwt < logwt_old:
            ndecl += 1
        else:
            ndecl = 0
        if ndecl > 10 and ndecl > it / 6:
            break
        logwt_old = logwt

    tottime = time.time() - time0
    if verbose:
        print 'calls={:d} time={:7.3f}s'.format(loglcalls, tottime)

    # Add remaining objects.
    # After N samples have been taken out, the remaining width is e^(-N/nobj)
    # The remaining width for each object is e^(-N/nobj) / nobj
    # The log of this for each object is:
    # log(e^(-N/nobj) / nobj) = -N/nobj - log(nobj)
    logwidth = -len(samples_parvals) / nobj - math.log(nobj)
    for i in range(nobj):
        logwt = logwidth + objects_logl[i]
        logz_new = np.logaddexp(logz, logwt)
        h = (math.exp(logwt - logz_new) * objects_logl[i] +
             math.exp(logz - logz_new) * (h + logz) -
             logz_new)
        logz = logz_new
        samples_parvals.append(np.array(objects_v[i]))
        samples_logwt.append(logwt)

    return {
        'niter': it + 1,
        'ncalls': loglcalls,
        'time': tottime,
        'logz': logz,
        'logzerr': math.sqrt(h / nobj),
        'loglmax': np.max(objects_logl),
        'h': h,
        'samples_parvals': np.array(samples_parvals),  #(nsamp, npar)
        'samples_wt':  np.exp(np.array(samples_logwt) - logz)  #(nsamp,)
        }
