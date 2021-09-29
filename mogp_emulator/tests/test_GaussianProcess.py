from tempfile import TemporaryFile
import numpy as np
import pytest
from numpy.testing import assert_allclose
from ..LibGPGPU import gpu_usable
from ..GaussianProcess import GaussianProcess, PredictResult
from ..GaussianProcessGPU import GaussianProcessGPU
from ..Kernel import SquaredExponential, Matern52
from ..GPParams import GPParams
from ..Priors import GPPriors, NormalPrior, LogNormalPrior, GammaPrior, InvGammaPrior
from ..Priors import WeakPrior, MeanPriors
from scipy import linalg

GPU_NOT_FOUND_MSG = "A compatible GPU could not be found or the GPU library (libgpgpu) could not be loaded"

@pytest.fixture
def x():
    return np.array([[1., 2., 3.], [4., 5., 6.]])

@pytest.fixture
def y():
    return np.array([2., 4.])

def test_GaussianProcess_init(x, y):
    "Test function for correct functioning of the init method of GaussianProcess"

    gp = GaussianProcess(x, y)
    assert_allclose(x, gp.inputs)
    assert_allclose(y, gp.targets)
    assert gp.D == 3
    assert gp.n == 2
    assert gp.nugget == None

    gp = GaussianProcess(y, y)
    assert gp.inputs.shape == (2, 1)

    gp = GaussianProcess(x, y, nugget=1.e-12)
    assert_allclose(gp.nugget, 1.e-12)

    gp = GaussianProcess(x, y, mean="1", kernel=Matern52(), nugget="fit")
    assert gp._dm.shape == (2, 1)

    gp = GaussianProcess(x, y, kernel="SquaredExponential")
    assert isinstance(gp.kernel, SquaredExponential)

    gp = GaussianProcess(x, y, kernel="Matern52")
    assert isinstance(gp.kernel, Matern52)

    gp = GaussianProcess(x, y, mean="0")
    assert gp._dm.shape == (2, 0)
    
    gp = GaussianProcess(x, y, mean="-1")
    assert gp._dm.shape == (2, 0)
    
    gp = GaussianProcess(x, y, mean="x[0]")
    assert gp._dm.shape == (2, 2)


@pytest.mark.skipif(not gpu_usable(), reason=GPU_NOT_FOUND_MSG)
def test_GaussianProcessGPU_init(x, y):
    "Test function for correct functioning of the init method of GaussianProcess"

    gp = GaussianProcessGPU(x, y)
    assert_allclose(x, gp.inputs)
    assert_allclose(y, gp.targets)
    assert gp.D == 3
    assert gp.n == 2
    assert gp.nugget == None
    assert gp.nugget_type == "adaptive"
    gp = GaussianProcessGPU(y, y)
    assert gp.inputs.shape == (2, 1)

    gp = GaussianProcessGPU(x, y, nugget=1.e-12)
    assert_allclose(gp.nugget, 1.e-12)
    from ..LibGPGPU import kernel_type
    gp = GaussianProcessGPU(x, y, kernel="SquaredExponential")
    assert isinstance(gp.kernel_type, kernel_type)
    assert gp.kernel_type is kernel_type.SquaredExponential
    assert isinstance(gp.kernel, SquaredExponential)

def test_GP_init_failures(x, y):
    "Tests that GaussianProcess fails correctly with bad inputs"

    with pytest.raises(AssertionError):
        gp = GaussianProcess(np.ones((2, 2, 2)), y)

    with pytest.raises(AssertionError):
        gp = GaussianProcess(x, x)

    with pytest.raises(AssertionError):
        gp = GaussianProcess(np.ones((2, 3)), np.ones(3))

    with pytest.raises(ValueError):
        gp = GaussianProcess(x, y, mean=1.)

    with pytest.raises(ValueError):
        gp = GaussianProcess(x, y, kernel="blah")

    with pytest.raises(ValueError):
        gp = GaussianProcess(x, y, kernel=1)

    with pytest.raises(ValueError):
        gp = GaussianProcess(x, y, nugget="a")


@pytest.mark.skipif(not gpu_usable(), reason=GPU_NOT_FOUND_MSG)
def test_GPGPU_init_failures(x, y):
    "Tests that GaussianProcessGPU fails correctly with bad inputs"

    with pytest.raises(AssertionError):
        gp = GaussianProcessGPU(np.ones((2, 2, 2)), y)

    with pytest.raises(AssertionError):
        gp = GaussianProcessGPU(x, x)

    with pytest.raises(AssertionError):
        gp = GaussianProcessGPU(np.ones((2, 3)), np.ones(3))

    with pytest.raises(ValueError):
        gp = GaussianProcessGPU(x, y, mean=1)

    with pytest.raises(ValueError):
        gp = GaussianProcessGPU(x, y, kernel="blah")

    with pytest.raises(ValueError):
        gp = GaussianProcessGPU(x, y, kernel=1)

    with pytest.raises(ValueError):
        gp = GaussianProcessGPU(x, y, nugget="a")

def test_GaussianProcess_n_params(x, y):
    "test the get_n_params method of GaussianProcess"

    gp = GaussianProcess(x, y)
    assert gp.n_params == x.shape[1] + 2

    gp = GaussianProcess(x, y, mean="x[0]")
    assert gp.n_params == 2 + x.shape[1] + 2


@pytest.mark.skipif(not gpu_usable(), reason=GPU_NOT_FOUND_MSG)
def test_GaussianProcessGPU_n_params(x, y):
    "test the get_n_params method of GaussianProcessGPU"

    gp = GaussianProcessGPU(x, y)
    assert gp.n_params == x.shape[1] + 2

def test_GaussianProcess_nugget(x, y):
    "Tests the get_nugget method of GaussianProcess"

    gp = GaussianProcess(x, y)
    assert gp.nugget is None
    assert gp.nugget_type == "adaptive"

    gp.nugget = "fit"
    assert gp.nugget is None
    assert gp.nugget_type == "fit"

    gp.nugget = 1.
    assert_allclose(gp.nugget, 1.)
    assert gp.nugget_type == "fixed"

    gp.nugget = 0
    assert_allclose(gp.nugget, 0.)
    assert gp.nugget_type == "fixed"

    gp.nugget = "pivot"
    assert gp.nugget is None
    assert gp.nugget_type == "pivot"

    with pytest.raises(TypeError):
        gp.nugget = [1]

    with pytest.raises(ValueError):
        gp.nugget = "blah"

    with pytest.raises(ValueError):
        gp.nugget = -1.


@pytest.mark.skipif(not gpu_usable(), reason=GPU_NOT_FOUND_MSG)
def test_GaussianProcessGPU_nugget(x, y):
    "Tests the get_nugget method of GaussianProcessGPU"

    gp = GaussianProcessGPU(x, y)
    assert gp.nugget is None
    assert gp.nugget_type == "adaptive"

    gp.nugget = "fit"
    assert gp.nugget is None
    assert gp.nugget_type == "fit"

    gp.nugget = 1.
    assert_allclose(gp.nugget, 1.)
    assert gp.nugget_type == "fixed"

    gp.nugget = 0
    assert_allclose(gp.nugget, 0.)
    assert gp.nugget_type == "fixed"

    with pytest.raises(TypeError):
        gp.nugget = [1]

    with pytest.raises(ValueError):
        gp.nugget = "blah"

    with pytest.raises(ValueError):
        gp.nugget = -1.

@pytest.mark.parametrize("mean,nugget,sn", [(None, 0., 1.), (None, "adaptive", 0.),
                                            (None, "pivot", 0.),
                                            ("x[0]", "fit", np.log(1.e-6))])
def test_GaussianProcess_theta(x, y, mean, nugget, sn):
    "test the theta property of GaussianProcess (effectively the same as fit)"

    if isinstance(nugget, float):
        nugget_type = "fixed"
    else:
        nugget_type = nugget

    gp = GaussianProcess(x, y, mean=mean, nugget=nugget, priors=GPPriors(n_corr=3, nugget_type=nugget_type))

    with pytest.raises(AssertionError):
        gp.theta = np.ones(gp.n_params + 1)

    theta = np.ones(gp.n_params)
    if not nugget == "pivot":
        theta[-1] = sn

    gp.theta = theta

    switch = gp.theta.n_mean

    if nugget == "adaptive" or nugget == 0. or nugget == "pivot":
        assert gp.nugget == 0.
        noise = 0.
    else:
        assert_allclose(gp.nugget, np.exp(sn))
        noise = np.exp(sn)*np.eye(x.shape[0])
    Q = gp.kernel.kernel_f(x, x, theta[switch:(switch + gp.D + 1)]) + noise
    ym = y - np.dot(gp._dm, theta[:switch])

    L_expect = np.linalg.cholesky(Q)
    invQt_expect = np.linalg.solve(Q, ym)
    logpost_expect = 0.5*(np.log(np.linalg.det(Q)) +
                          np.dot(ym, invQt_expect) +
                          gp.n*np.log(2.*np.pi))

    assert_allclose(L_expect, gp.L)
    assert_allclose(invQt_expect, gp.invQt)
    assert_allclose(logpost_expect, gp.current_logpost)

def test_GaussianProcess_theta_GPParams(x, y):
    "test that we can set parameters using a GPParams object"

    gp = GaussianProcess(x, y)

    gpp = GPParams(n_corr=3, data=np.ones(gp.n_params))

    gp.theta = gpp

    assert_allclose(gp.theta.data, np.ones(gp.n_params))

    with pytest.raises(AssertionError):
        gp.theta = GPParams()

@pytest.mark.skipif(not gpu_usable(), reason=GPU_NOT_FOUND_MSG)
@pytest.mark.parametrize("nugget,sn", [(0., 1.), ("adaptive", 0.)]) # ("fit", np.log(1.e-6))])
def test_GaussianProcessGPU_theta(x, y, nugget, sn):
    "test the theta property of GaussianProcess (effectively the same as fit)"

    # zero mean, zero nugget

    gp = GaussianProcessGPU(x, y, nugget=nugget)

    theta = np.ones(gp.n_params)
    theta[-1] = sn

    gp.theta = theta

    if nugget == "adaptive" or nugget == 0.:
        assert gp.nugget == 0.
        noise = 0.
    else:
        assert_allclose(gp.nugget, np.exp(sn))
        noise = np.exp(sn)*np.eye(x.shape[0])
    Q = gp.kernel.kernel_f(x, x, theta[:-1]) + noise

    L_expect = np.linalg.cholesky(Q)
    invQt_expect = np.linalg.solve(Q, y)
    logpost_expect = 0.5*(np.log(np.linalg.det(Q)) +
                          np.dot(y, invQt_expect) +
                          gp.n*np.log(2.*np.pi))

    assert_allclose(L_expect, gp.L)
    assert_allclose(invQt_expect, gp.invQt)
    assert_allclose(logpost_expect, gp.current_logpost)

def test_GaussianProcess_theta_pivot():
    "test that pivoting works as expected"

    # input arrays are re-ordered such that pivoting should re-order the second to match the first

    x1 = np.array([1., 4., 2.])
    x2 = np.array([1., 2., 4.])
    y1 = np.array([1., 1., 2.])
    y2 = np.array([1., 2., 1.])

    gp1 = GaussianProcess(x1, y1, nugget=0.)
    gp2 = GaussianProcess(x2, y2, nugget="pivot")

    gp1.theta = np.zeros(3)
    gp2.theta = np.zeros(2)

    assert_allclose(gp1.L, gp2.L)
    assert_allclose(gp1.invQt, gp2.invQt[gp2.P])
    assert np.array_equal(gp2.P, [0, 2, 1])

def test_GaussianProcess_priors_property(x, y):
    "test that priors are set properly"

    gp = GaussianProcess(x, y)

    assert isinstance(gp.priors.mean, MeanPriors)
    assert gp.priors.mean.mean is None
    assert gp.priors.mean.cov is None
    for p in gp.priors.corr:
        assert isinstance(p, WeakPrior)
    assert isinstance(gp.priors.cov, WeakPrior)
    assert isinstance(gp.priors.nugget, WeakPrior)

    gp = GaussianProcess(x, y, priors=None)

    assert isinstance(gp.priors.mean, MeanPriors)
    assert gp.priors.mean.mean is None
    assert gp.priors.mean.cov is None
    for p in gp.priors.corr:
        assert isinstance(p, WeakPrior)
    assert isinstance(gp.priors.cov, WeakPrior)
    assert isinstance(gp.priors.nugget, WeakPrior)

    priors = GPPriors(n_corr=3, nugget_type="adaptive")
    gp = GaussianProcess(x, y, priors=priors)

    assert isinstance(gp.priors.mean, MeanPriors)
    assert gp.priors.mean.mean is None
    assert gp.priors.mean.cov is None
    for p in gp.priors.corr:
        assert isinstance(p, WeakPrior)
    assert isinstance(gp.priors.cov, WeakPrior)
    assert isinstance(gp.priors.nugget, WeakPrior)
    
    priors = {"mean": None, "corr": [LogNormalPrior(2., 2.), WeakPrior(), WeakPrior()], "cov": GammaPrior(3., 1.),
              "nugget_type": "adaptive"}
    gp = GaussianProcess(x, y, priors=priors)

    assert isinstance(gp.priors.mean, MeanPriors)
    assert gp.priors.mean.mean is None
    assert gp.priors.mean.cov is None
    assert isinstance(gp.priors.corr[0], LogNormalPrior)
    assert isinstance(gp.priors.corr[1], WeakPrior)
    assert isinstance(gp.priors.corr[2], WeakPrior)
    assert isinstance(gp.priors.cov, GammaPrior)
    assert isinstance(gp.priors.nugget, WeakPrior)

    priors = {"mean": None, "corr": [LogNormalPrior(2., 2.), WeakPrior(), WeakPrior()], "cov": GammaPrior(3., 1.),
              "nugget_type": "adaptive", "nugget": InvGammaPrior(3., 3.)}
    gp = GaussianProcess(x, y, priors=priors)

    assert isinstance(gp.priors.nugget, WeakPrior)
    
    with pytest.raises(AssertionError):
        priors = GPPriors(n_corr=3, nugget_type="fit")
        gp = GaussianProcess(x, y, priors=priors)
        
    with pytest.raises(AssertionError):
        priors = GPPriors(n_corr=4, nugget_type="adaptive")
        gp = GaussianProcess(x, y, priors=priors)

    with pytest.raises(TypeError):
        GaussianProcess(x, y, priors=1.)

    x = np.array([[1., 1.], [2., 2.], [4., 4.]])
    y = np.array([2., 4., 6.])

    gp = GaussianProcess(x, y, mean="1", priors={"mean": (np.array([1.]), np.array([1.])), "n_corr": 2,
                                                 "nugget_type": "adaptive"})

    assert_allclose(gp.priors.mean.mean, [1.])
    assert_allclose(gp.priors.mean.cov, [1.])
    
    gp = GaussianProcess(x, y, mean="1", priors={"mean": None, "n_corr": 2, "nugget_type": "adaptive"})
    
    with pytest.raises(AssertionError):
        gp = GaussianProcess(x, y, mean="1", priors={"mean": (np.array([1., 2.]), np.array([1., 2.])), "n_corr": 2,
                                                     "nugget_type": "adaptive"})


@pytest.mark.parametrize("mean,nugget,sn", [(None, 0., 1.), (None, "adaptive", 0.),
                                            (None, "pivot", 0.),
                                            ("x[0]", "fit", np.log(1.e-6))])
def test_GaussianProcess_fit_logposterior(x, y, mean, nugget, sn):
    "test the fit and logposterior methods of GaussianProcess"

    if isinstance(nugget, float):
        nugget_type = "fixed"
    else:
        nugget_type = nugget

    gp = GaussianProcess(x, y, mean=mean, nugget=nugget, priors=GPPriors(n_corr=3, nugget_type=nugget_type))

    with pytest.raises(AssertionError):
        gp.theta = np.ones(gp.n_params + 1)

    theta = np.ones(gp.n_params)
    if not nugget == "pivot":
        theta[-1] = sn

    gp.fit(theta)

    switch = gp.theta.n_mean

    if nugget == "adaptive" or nugget == 0. or nugget == "pivot":
        assert gp.nugget == 0.
        noise = 0.
    else:
        assert_allclose(gp.nugget, np.exp(sn))
        noise = np.exp(sn)*np.eye(x.shape[0])
    Q = gp.kernel.kernel_f(x, x, theta[switch:(switch + gp.D + 1)]) + noise
    ym = y - np.dot(gp._dm, theta[:switch])

    L_expect = np.linalg.cholesky(Q)
    invQt_expect = np.linalg.solve(Q, ym)
    logpost_expect = 0.5*(np.log(np.linalg.det(Q)) +
                          np.dot(ym, invQt_expect) +
                          gp.n*np.log(2.*np.pi))

    assert_allclose(L_expect, gp.L)
    assert_allclose(invQt_expect, gp.invQt)
    assert_allclose(logpost_expect, gp.current_logpost)
    assert_allclose(logpost_expect, gp.logposterior(theta))

def test_GaussianProcess_logposterior(x, y):
    "test logposterior method of GaussianProcess"

    # logposterior already tested, but check that parameters are re-fit if changed

    gp = GaussianProcess(x, y, nugget = 0., priors=GPPriors(n_corr=3, nugget_type="fixed"))

    theta = np.ones(gp.n_params)
    gp.fit(theta)

    theta = np.zeros(gp.n_params)

    Q = gp.kernel.kernel_f(x, x, theta[:-1])

    L_expect = np.linalg.cholesky(Q)
    invQt_expect = np.linalg.solve(Q, y)
    logpost_expect = 0.5*(np.log(np.linalg.det(Q)) +
                          np.dot(y, invQt_expect) +
                          gp.n*np.log(2.*np.pi))

    assert_allclose(logpost_expect, gp.logposterior(theta))
    assert_allclose(gp.L, L_expect)
    assert_allclose(invQt_expect, gp.invQt)
    assert_allclose(logpost_expect, gp.current_logpost)

    # check we can set theta back to none correctly

    gp.theta = None
    assert gp.theta.data is None
    assert gp.L is None
    assert gp.P is None
    assert gp.current_logpost is None

@pytest.mark.skipif(not gpu_usable(), reason=GPU_NOT_FOUND_MSG)
def test_GaussianProcessGPU_logposterior(x, y):
    "test logposterior method of GaussianProcessGPU"

    # logposterior already tested, but check that parameters are re-fit if changed

    gp = GaussianProcessGPU(x, y, nugget = 0.)

    theta = np.ones(gp.n_params)
    gp.fit(theta)

    theta = np.zeros(gp.n_params)

    Q = gp.kernel.kernel_f(x, x, theta[:-1])

    L_expect = np.linalg.cholesky(Q)
    invQt_expect = np.linalg.solve(Q, y)
    logpost_expect = 0.5*(np.log(np.linalg.det(Q)) +
                          np.dot(y, invQt_expect) +
                          gp.n*np.log(2.*np.pi))

    assert_allclose(logpost_expect, gp.logposterior(theta))
    assert_allclose(gp.L, L_expect)
    assert_allclose(invQt_expect, gp.invQt)
    assert_allclose(logpost_expect, gp.current_logpost)

@pytest.fixture
def dx():
    return 1.e-6

@pytest.mark.parametrize("mean,nugget,sn", [(None, 0., 1.), (None, "adaptive", 1.),
                                            (None, "pivot", 1.),
                                            ("x[0]", "fit", np.log(1.e-6))])
def test_GaussianProcess_logpost_deriv(x, y, dx, mean, nugget, sn):
    "test logposterior derivatives for GaussianProcess via finite differences"

    if isinstance(nugget, float):
        nugget_type = "fixed"
    else:
        nugget_type = nugget

    gp = GaussianProcess(x, y, mean=mean, nugget=nugget, priors=GPPriors(n_corr=3, nugget_type=nugget_type))

    n = gp.n_params
    theta = np.ones(n)
    theta[-1] = sn

    deriv = np.zeros(n)

    for i in range(n):
        dx_array = np.zeros(n)
        dx_array[i] = dx
        deriv[i] = (gp.logposterior(theta) - gp.logposterior(theta - dx_array))/dx

    assert_allclose(deriv, gp.logpost_deriv(theta), atol=1.e-7, rtol=1.e-5)

@pytest.mark.skipif(not gpu_usable(), reason=GPU_NOT_FOUND_MSG)
@pytest.mark.parametrize("nugget,sn", [(0., 1.), ("adaptive", 1.),
                                            ("fit", np.log(1.e-6))])
def test_GaussianProcessGPU_logpost_deriv(x, y, dx, nugget, sn):
    "test logposterior derivatives for GaussianProcessGPU via finite differences"

    gp = GaussianProcessGPU(x, y, nugget=nugget)

    n = gp.n_params
    theta = np.ones(n)
    theta[-1] = sn

    deriv = np.zeros(n)

    for i in range(n):
        dx_array = np.zeros(n)
        dx_array[i] = dx
        deriv[i] = (gp.logposterior(theta) - gp.logposterior(theta - dx_array))/dx

    assert_allclose(deriv, gp.logpost_deriv(theta), atol=1.e-7, rtol=1.e-5)

@pytest.mark.parametrize("mean,nugget,sn", [(None, 0., 1.),
                                            (None, "pivot", 1.), ("x[0]", "fit", np.log(1.e-6))])
def test_GaussianProcess_logpost_hessian(x, y, dx, mean, nugget, sn):
    "test the hessian method of GaussianProcess with finite differences"

    # zero mean, no nugget

    if isinstance(nugget, float):
        nugget_type = "fixed"
    else:
        nugget_type = nugget

    gp = GaussianProcess(x, y, mean=mean, nugget=nugget, priors=GPPriors(n_corr=3, nugget_type=nugget_type))

    n = gp.n_params
    theta = np.ones(n)
    theta[-1] = sn

    hess = np.zeros((n, n))

    for i in range(n):
        for j in range(n):
            dx_array = np.zeros(n)
            dx_array[j] = dx
            hess[i, j] = (gp.logpost_deriv(theta)[i] - gp.logpost_deriv(theta - dx_array)[i])/dx

    assert_allclose(hess, gp.logpost_hessian(theta), rtol=1.e-5, atol=1.e-7)

def test_GaussianProcess_default_priors(dx):
    "test that the default priors work as expected"

    x = np.array([[1., 1.], [2., 2.], [4., 4.]])
    y = np.array([2., 4., 6.])

    gp = GaussianProcess(x, y, nugget=0.)

    theta = np.zeros(gp.n_params)

    gp.fit(theta)

    Q = gp.get_K_matrix()

    L_expect = np.linalg.cholesky(Q)
    invQt_expect = np.linalg.solve(Q, y)
    logpost_expect = 0.5*(np.log(np.linalg.det(Q)) +
                          np.dot(y, invQt_expect) +
                          gp.n*np.log(2.*np.pi))

    dist = InvGammaPrior.default_prior_corr(np.array([1., 2., 4.]))

    logpost_expect -= 2.*dist.logp(1.)

    assert_allclose(L_expect, gp.L)
    assert_allclose(invQt_expect, gp.invQt)
    assert_allclose(logpost_expect, gp.current_logpost)
    assert_allclose(logpost_expect, gp.logposterior(theta))

    n = gp.n_params
    deriv = np.zeros(n)

    for i in range(n):
        dx_array = np.zeros(n)
        dx_array[i] = dx
        deriv[i] = (gp.logposterior(theta) - gp.logposterior(theta - dx_array))/dx

    assert_allclose(deriv, gp.logpost_deriv(theta), atol=1.e-5, rtol=1.e-5)

    hess = np.zeros((n, n))

    for i in range(n):
        for j in range(n):
            dx_array = np.zeros(n)
            dx_array[j] = dx
            hess[i, j] = (gp.logpost_deriv(theta)[i] - gp.logpost_deriv(theta - dx_array)[i])/dx

    assert_allclose(hess, gp.logpost_hessian(theta), rtol=1.e-5, atol=1.e-5)

@pytest.mark.parametrize("priors,nugget,sn", [({"corr": [ LogNormalPrior(0.9, 0.5), WeakPrior(), LogNormalPrior(0.5, 2.)],
                                               "cov": InvGammaPrior(2., 1.), "nugget_type": "fixed"}, 0., 0.),
                                           ( {"corr": [ WeakPrior(), LogNormalPrior(1.2, 0.2), WeakPrior()],
                                              "cov": GammaPrior(2., 1.), "nugget": InvGammaPrior(2., 1.e-6),
                                              "nugget_type": "fit"}, "fit", np.log(1.e-6))])
def test_GaussianProcess_priors(x, y, dx, priors, nugget, sn):
    "test that prior distributions are properly accounted for in posterior"

    gp = GaussianProcess(x, y, mean="1", priors=priors, nugget=nugget)

    theta = np.ones(gp.n_params)
    theta[0] = 0.5
    theta[-1] = sn

    gp.fit(theta)

    if nugget == 0.:
        noise = 0.
    else:
        assert_allclose(gp.nugget, np.exp(sn))
        noise = np.exp(sn)*np.eye(x.shape[0])
    Q = gp.get_K_matrix() + noise

    L_expect = np.linalg.cholesky(Q)
    invQt_expect = np.linalg.solve(Q, y - theta[0])
    logpost_expect = 0.5*(np.log(np.linalg.det(Q)) +
                          np.dot(y - theta[0], invQt_expect) +
                          gp.n*np.log(2.*np.pi))

    theta_transformed = np.zeros(gp.n_params)
    theta_transformed[0] = theta[0]
    theta_transformed[1:4] = np.exp(-0.5*theta[1:4])
    theta_transformed[4:] = np.exp(theta[4:])
    for p, t in zip(gp.priors.corr, theta_transformed[1:4]):
        logpost_expect -= p.logp(t)
    logpost_expect -= gp.priors.cov.logp(theta_transformed[4])
    if nugget == "fit":
        logpost_expect -= gp.priors.nugget.logp(theta_transformed[-1])

    assert_allclose(L_expect, gp.L)
    assert_allclose(invQt_expect, gp.invQt)
    assert_allclose(logpost_expect, gp.current_logpost)
    assert_allclose(logpost_expect, gp.logposterior(theta))

    n = gp.n_params
    deriv = np.zeros(n)

    for i in range(n):
        dx_array = np.zeros(n)
        dx_array[i] = dx
        deriv[i] = (gp.logposterior(theta) - gp.logposterior(theta - dx_array))/dx

    assert_allclose(deriv, gp.logpost_deriv(theta), atol=1.e-5, rtol=1.e-5)

    hess = np.zeros((n, n))

    for i in range(n):
        for j in range(n):
            dx_array = np.zeros(n)
            dx_array[j] = dx
            hess[i, j] = (gp.logpost_deriv(theta)[i] - gp.logpost_deriv(theta - dx_array)[i])/dx

    assert_allclose(hess, gp.logpost_hessian(theta), rtol=1.e-5, atol=1.e-5)

def test_GaussianProcess_predict(x, y, dx):
    "test the predict method of GaussianProcess"

    # zero mean

    gp = GaussianProcess(x, y, nugget=0.)
    theta = np.ones(gp.n_params)

    gp.fit(theta)

    x_test = np.array([[2., 3., 4.]])

    mu, var, deriv = gp.predict(x_test)

    K = gp.kernel.kernel_f(x, x, theta[:-1])
    Ktest = gp.kernel.kernel_f(x_test, x, theta[:-1])

    mu_expect = np.dot(Ktest, gp.invQt)
    var_expect = np.exp(theta[-2]) - np.diag(np.dot(Ktest, np.linalg.solve(K, Ktest.T)))

    assert_allclose(mu, mu_expect)
    assert_allclose(var, var_expect)

    # check that reshaping works as expected

    x_test = np.array([2., 3., 4.])

    mu, var, deriv = gp.predict(x_test)

    assert_allclose(mu, mu_expect)
    assert_allclose(var, var_expect)

    # check that with 1D input data can handle 1D prediction data correctly

    gp = GaussianProcess(y, y, nugget=0.)

    gp.fit(np.ones(gp.n_params))

    n_predict = 51
    mu, var, deriv = gp.predict(np.linspace(0., 1., n_predict))

    assert mu.shape == (n_predict,)
    assert var.shape == (n_predict,)

    # nonzero mean function

    gp = GaussianProcess(x, y, mean="x[0]", nugget=0.)

    theta = np.ones(gp.n_params)

    gp.fit(theta)

    x_test = np.array([[2., 3., 4.]])

    mu, var, deriv = gp.predict(x_test)

    switch = gp.theta.n_mean
    m = np.dot(gp.get_design_matrix(x_test), theta[:switch])
    K = gp.kernel.kernel_f(x, x, theta[switch:-1])
    Ktest = gp.kernel.kernel_f(x_test, x, theta[switch:-1])

    mu_expect = m + np.dot(Ktest, gp.invQt)

    assert_allclose(mu, mu_expect)
    assert_allclose(var, var_expect)

    # check unc and deriv flags work

    _, var, deriv = gp.predict(x_test, unc=False, deriv=False)

    assert var is None
    assert deriv is None

    # check that the returned PredictResult works correctly

    pr = gp.predict(x_test)

    assert_allclose(pr.mean, mu_expect)
    assert_allclose(pr.unc, var_expect)
    assert pr.deriv is None

    assert_allclose(pr['mean'], mu_expect)
    assert_allclose(pr['unc'], var_expect)
    assert pr["deriv"] is None

    assert_allclose(pr[0], mu_expect)
    assert_allclose(pr[1], var_expect)
    assert pr[2] is None

    # check that calling gp is equivalent to predicting

    assert_allclose(gp(x_test), mu_expect)

@pytest.mark.skipif(not gpu_usable(), reason=GPU_NOT_FOUND_MSG)
def test_GaussianProcessGPU_predict(x, y, dx):
    "test the predict method of GaussianProcessGPU"

    # zero mean

    gp = GaussianProcessGPU(x, y, nugget=0.)
    theta = np.ones(gp.n_params)

    gp.fit(theta)

    x_test = np.array([[2., 3., 4.]])

    mu, var, deriv = gp.predict(x_test)

    K = gp.kernel.kernel_f(x, x, theta[:-1])
    Ktest = gp.kernel.kernel_f(x_test, x, theta[:-1])

    mu_expect = np.dot(Ktest, gp.invQt)
    var_expect = np.exp(theta[-2]) - np.diag(np.dot(Ktest, np.linalg.solve(K, Ktest.T)))

    D = gp.D

    deriv_expect = np.zeros((1, D))

    for i in range(D):
        dx_array = np.zeros(D)
        dx_array[i] = dx
        deriv_expect[0, i] = (gp.predict(x_test)[0] - gp.predict(x_test - dx_array)[0])/dx

    assert_allclose(mu, mu_expect)
    assert_allclose(var, var_expect)
    assert_allclose(deriv, deriv_expect, atol=1.e-7, rtol=1.e-7)

    # check that reshaping works as expected

    x_test = np.array([2., 3., 4.])

    mu, var, deriv = gp.predict(x_test)

    assert_allclose(mu, mu_expect)
    assert_allclose(var, var_expect)
    assert_allclose(deriv, deriv_expect, atol=1.e-7, rtol=1.e-7)

    # check that with 1D input data can handle 1D prediction data correctly

    gp = GaussianProcessGPU(y, y, nugget=0.)

    gp.fit(np.ones(gp.n_params))

    n_predict = 51
    mu, var, deriv = gp.predict(np.linspace(0., 1., n_predict))

    assert mu.shape == (n_predict,)
    assert var.shape == (n_predict,)
    assert deriv.shape == (n_predict, 1)

    # check unc and deriv flags work

    _, var, deriv = gp.predict(x_test, unc=False, deriv=False)

    assert var is None
    assert deriv is None

    # check that the returned PredictResult works correctly
    gp = GaussianProcessGPU(x, y, nugget=0.)
    theta = np.ones(gp.n_params)
    gp.fit(theta)
    x_test = np.array([[2., 3., 4.]])

    pr = gp.predict(x_test)

    assert_allclose(pr.mean, mu_expect)
    assert_allclose(pr.unc, var_expect)
    assert_allclose(pr.deriv, deriv_expect, atol=1.e-7, rtol=1.e-7)

    assert_allclose(pr['mean'], mu_expect)
    assert_allclose(pr['unc'], var_expect)
    assert_allclose(pr['deriv'], deriv_expect, atol=1.e-7, rtol=1.e-7)

    assert_allclose(pr[0], mu_expect)
    assert_allclose(pr[1], var_expect)
    assert_allclose(pr[2], deriv_expect, atol=1.e-7, rtol=1.e-7)

    # check that calling gp is equivalent to predicting

    assert_allclose(gp(x_test), mu_expect)

def test_GaussianProcess_predict_nugget(x, y):
    "test that the nugget works correctly when making predictions"

    nugget = 1.e0

    gp = GaussianProcess(x, y, nugget=nugget)
    theta = np.ones(gp.n_params)

    gp.fit(theta)

    preds = gp.predict(x)

    K = gp.kernel.kernel_f(x, x, theta[:-1])

    var_expect = np.exp(theta[-2]) + nugget - np.diag(np.dot(K, np.linalg.solve(K + np.eye(gp.n)*nugget, K)))

    assert_allclose(preds.unc, var_expect, atol=1.e-7)

    preds = gp.predict(x, include_nugget=False)

    var_expect = np.exp(theta[-2]) - np.diag(np.dot(K, np.linalg.solve(K + np.eye(gp.n)*nugget, K)))

    assert_allclose(preds.unc, var_expect, atol=1.e-7)


@pytest.mark.skipif(not gpu_usable(), reason=GPU_NOT_FOUND_MSG)
def test_GaussianProcessGPU_predict_nugget(x, y):
    "test that the nugget works correctly when making predictions"

    nugget = 1.e0

    gp = GaussianProcessGPU(x, y, nugget=nugget)
    theta = np.ones(gp.n_params)

    gp.fit(theta)

    preds = gp.predict(x)

    K = gp.kernel.kernel_f(x, x, theta[:-1])

    var_expect = np.exp(theta[-2]) + nugget - np.diag(np.dot(K, np.linalg.solve(K + np.eye(gp.n)*nugget, K)))

    assert_allclose(preds.unc, var_expect, atol=1.e-7)

    preds = gp.predict(x, include_nugget=False)

    var_expect = np.exp(theta[-2]) - np.diag(np.dot(K, np.linalg.solve(K + np.eye(gp.n)*nugget, K)))

    assert_allclose(preds.unc, var_expect, atol=1.e-7)

def test_GaussianProcess_predict_pivot():
    "test that pivoting gives same predictions as standard version"

    # input arrays are re-ordered such that pivoting should re-order the second to match the first

    x1 = np.array([1., 4., 2.])
    x2 = np.array([1., 2., 4.])
    y1 = np.array([1., 1., 2.])
    y2 = np.array([1., 2., 1.])

    gp1 = GaussianProcess(x1, y1, nugget=0.)
    gp2 = GaussianProcess(x2, y2, nugget="pivot")

    gp1.theta = np.zeros(3)
    gp2.theta = np.zeros(2)

    xpred = np.linspace(0., 5.)

    mean1, var1, deriv1 = gp1.predict(xpred)
    mean2, var2, deriv2 = gp2.predict(xpred)

    assert_allclose(mean1, mean2)
    assert_allclose(var1, var2)

def test_GaussianProcess_predict_variance():
    "confirm that caching factorized matrix produces stable variance predictions"

    x = np.linspace(0., 5., 21)
    y = x**2
    x = np.reshape(x, (-1, 1))
    nugget = 1.e-8

    gp = GaussianProcess(x, y, nugget=nugget)

    theta = np.array([-7.352408190715323, 15.041447753599755, 0.])
    gp.fit(theta)

    testing = np.reshape(np.linspace(0., 5., 101), (-1, 1))

    _, var, _ = gp.predict(testing)

    assert_allclose(np.zeros(101), var, atol = 1.e-3)

def test_GaussianProcess_predict_failures(x, y):
    "test situations where predict method of GaussianProcess should fail"

    gp = GaussianProcess(x, y)

    with pytest.raises(ValueError):
        gp.predict(np.array([2., 3., 4.]))

    theta = np.ones(gp.n_params)
    gp.fit(theta)

    with pytest.raises(AssertionError):
        gp.predict(np.ones((2, 2, 2)))

    with pytest.raises(AssertionError):
        gp.predict(np.array([[2., 4.]]))


@pytest.mark.skipif(not gpu_usable(), reason=GPU_NOT_FOUND_MSG)
def test_GaussianProcessGPU_predict_failures(x, y):
    "test situations where predict method of GaussianProcessGPU should fail"

    gp = GaussianProcessGPU(x, y)

    with pytest.raises(ValueError):
        gp.predict(np.array([2., 3., 4.]))

    theta = np.ones(gp.n_params)
    gp.fit(theta)

    with pytest.raises(AssertionError):
        gp.predict(np.ones((2, 2, 2)))

    with pytest.raises(AssertionError):
        gp.predict(np.array([[2., 4.]]))


def test_GaussianProcess_str(x, y):
    "Test function for string method"

    gp = GaussianProcess(x, y)
    assert (str(gp) == "Gaussian Process with {} training examples and {} input variables".format(x.shape[0], x.shape[1]))


@pytest.mark.skipif(not gpu_usable(), reason=GPU_NOT_FOUND_MSG)
def test_GaussianProcessGPU_str(x, y):
    "Test function for string method"

    gp = GaussianProcessGPU(x, y)
    assert (str(gp) == "Gaussian Process with {} training examples and {} input variables".format(x.shape[0], x.shape[1]))
