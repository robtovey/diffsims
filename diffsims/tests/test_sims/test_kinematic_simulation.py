'''
Created on 3 Nov 2019

@author: Rob Tovey
'''

import pytest
import numpy as np
from diffsims.sims.kinematic_simulation import (get_diffraction_image, precess_mat, grid2sphere)


def toMesh(x):
    y = np.meshgrid(*x, indexing='ij')
    return np.concatenate([z[..., None] for z in y], axis=-1)


def create_atoms(n, shape):
    coords = np.concatenate(
        [np.linspace(0, s / 2, len(n)).reshape(-1, 1) for s in shape],
        axis=1)
    species = np.array(n)
    return coords, species


def probe(x, out=None, scale=None):
    if len(x) == 3:
        v = abs(x[0].reshape(-1, 1, 1)) < 6
        v = v * abs(x[1].reshape(1, -1, 1)) < 6
        v = v + 0 * x[2].reshape(1, 1, -1)
    else:
        v = abs(x[..., :2]).max(-1) < 6
    if scale is not None:
        v = v * scale
    if out is None:
        return v
    else:
        out[...] = v
        return out


@pytest.mark.parametrize('n, vol_shape, grid_shape, precession', [
    ([0], (.7, .7, .7), (10, 11, 12), False),
    ([10, 14], (10, 20, 30), (10, 10, 10), False),
    ([14], (5, 10, 15), (10,) * 3, True),
])
def test_get_diffraction_image(n, vol_shape, grid_shape, precession):
    coords, species = create_atoms(n, vol_shape)
    x = [np.linspace(0, vol_shape[i], grid_shape[i]) for i in range(3)]
    wavelength = 1e-8
    if precession:
        precession = (1e-2, 20)
    else:
        precession = (0, 1)

    val1 = get_diffraction_image(coords, species, probe, x, wavelength, precession, True)
    val2 = get_diffraction_image(coords, species, probe, x, 0, (0, 1), True)

    if precession[0] > 0:
        val1 = val1[2:-2, 2:-2]
        val2 = val2[2:-2, 2:-2]

    assert val1.shape == val2.shape
    if precession[0] == 0:
        assert val1.shape == grid_shape[:2]
    np.testing.assert_allclose(val1, val2, 1e-2, 1e-4)


@pytest.mark.parametrize('alpha, theta, x', [
    (0, 10, (-1, 0, 1)),
    (10, 0, (1, 2, 3)),
    (5, 10, (-1, 1, -1)),
])
def test_precess_mat(alpha, theta, x):
    R = precess_mat(alpha, theta)
    Ra = precess_mat(alpha, 0)
    Rt = precess_mat(theta, 0)[::-1, ::-1].T
    x = np.array(x)

    angle = lambda v1, v2: (v1 * v2).sum() / np.linalg.norm(v1) / np.linalg.norm(v2)

    np.testing.assert_allclose(np.cos(np.deg2rad(theta)), angle(x[:2], Rt.dot(x)[:2]), 1e-5, 1e-5)
    np.testing.assert_allclose(np.cos(np.deg2rad(alpha)), angle(x[1:], Ra.dot(x)[1:]), 1e-5, 1e-5)
    assert abs(R[2, 2] - np.cos(np.deg2rad(alpha))) < 1e-5
    assert abs(R - Rt.T.dot(Ra.dot(Rt))).max() < 1e-5


@pytest.mark.parametrize('shape, rad', [
    ((10,) * 3, 100),
    ((10, 20, 20), 200),
    ((10, 20, 30), 300),
])
def test_grid2sphere(shape, rad):
    x = [np.linspace(-1, 1, s) for s in shape]
    X = toMesh(x)
    Y = toMesh((x[0], x[1], np.array([0]))).reshape(-1, 3)
    w = 1 / (1 + (Y ** 2).sum(-1) / rad ** 2)
    Y *= w[..., None]
    Y[:, 2] = rad * (1 - w)
    Y = Y.reshape(shape[0], shape[1], 3)

    for i in range(3):
        np.testing.assert_allclose(Y[..., i], grid2sphere(X[..., i], x, None, rad), 1e-4, 1e-4)