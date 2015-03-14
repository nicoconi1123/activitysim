# ActivitySim
# Copyright (C) 2014-2015 Synthicity, LLC
# See full license in LICENSE.txt.

import os.path

import numpy as np
import pandas as pd
import pandas.util.testing as pdt
import pytest

from ..activitysim import eval_variables
from .. import mnl


@pytest.fixture
def seed(request):
    current = np.random.get_state()

    def fin():
        np.random.set_state(current)
    request.addfinalizer(fin)

    np.random.seed(0)


# this is lifted straight from urbansim's test_mnl.py
@pytest.fixture(scope='module', params=[
    ('fish.csv',
        'fish_choosers.csv',
        pd.DataFrame(
            [[-0.02047652], [0.95309824]], index=['price', 'catch'],
            columns=['Alt']),
        pd.DataFrame([
            [0.2849598, 0.2742482, 0.1605457, 0.2802463],
            [0.1498991, 0.4542377, 0.2600969, 0.1357664]],
            columns=['beach', 'boat', 'charter', 'pier']))])
def test_data(request):
    data, choosers, spec, probabilities = request.param
    return {
        'data': data,
        'choosers': choosers,
        'spec': spec,
        'probabilities': probabilities
    }


@pytest.fixture
def choosers(test_data):
    filen = os.path.join(
        os.path.dirname(__file__), 'data', test_data['choosers'])
    return pd.read_csv(filen)


@pytest.fixture
def spec(test_data):
    return test_data['spec']


@pytest.fixture
def choosers_dm(choosers, spec):
    return eval_variables(spec.index, choosers)


@pytest.fixture
def utilities(choosers_dm, spec, test_data):
    utils = choosers_dm.dot(spec).astype('float')
    return pd.DataFrame(
        utils.as_matrix().reshape(test_data['probabilities'].shape),
        columns=test_data['probabilities'].columns)


def test_utils_to_probs(utilities, test_data):
    probs = mnl.utils_to_probs(utilities)
    pdt.assert_frame_equal(probs, test_data['probabilities'])


def test_make_choices_only_one():
    probs = pd.DataFrame(
        [[1, 0, 0], [0, 1, 0]], columns=['a', 'b', 'c'], index=['x', 'y'])
    choices = mnl.make_choices(probs)

    pdt.assert_series_equal(
        choices,
        pd.Series([0, 1], index=['x', 'y']))


def test_make_choices_real_probs(seed, utilities):
    probs = mnl.utils_to_probs(utilities)
    choices = mnl.make_choices(probs)

    pdt.assert_series_equal(
        choices,
        pd.Series([1, 2], index=[0, 1]))
