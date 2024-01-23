# ==============================================================================
# Copyright 2024 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

import numpy as np
from sklearn.utils import check_array, gen_batches

from daal4py.sklearn._utils import control_n_jobs, run_with_n_jobs
from onedal._device_offload import support_usm_ndarray
from onedal.basic_statistics import (
    IncrementalBasicStatistics as onedal_IncrementalBasicStatistics,
)


@control_n_jobs
class IncrementalBasicStatistics:
    """
    Incremental estimator for basix statistics.
    Allows to compute basic statistics if data are splitted into batches.
    Parameters
    ----------
    result_options: string or list, default='all'
        List of statistics to compute

    batch_size : int, default=None
        The number of samples to use for each batch. Only used when calling
        ``fit``. If ``batch_size`` is ``None``, then ``batch_size``
        is inferred from the data and set to ``5 * n_features``, to provide a
        balance between approximation accuracy and memory consumption.

    Attributes (are existing only if corresponding result option exists)
    ----------
        min : ndarray of shape (n_features,)
            Minimum of each feature over all samples.

        max : ndarray of shape (n_features,)
            Maximum of each feature over all samples.

        sum : ndarray of shape (n_features,)
            Sum of each feature over all samples.

        mean : ndarray of shape (n_features,)
            Mean of each feature over all samples.

        variance : ndarray of shape (n_features,)
            Variance of each feature over all samples.

        variation : ndarray of shape (n_features,)
            Variation of each feature over all samples.

        sum_squares : ndarray of shape (n_features,)
            Sum of squares for each feature over all samples.

        standard_deviation : ndarray of shape (n_features,)
            Standard deviation of each feature over all samples.

        sum_squares_centered : ndarray of shape (n_features,)
            Centered sum of squares for each feature over all samples.

        second_order_raw_moment : ndarray of shape (n_features,)
            Second order moment of each feature over all samples.
    """

    _onedal_incremental_basic_statistics = staticmethod(onedal_IncrementalBasicStatistics)

    def __init__(self, result_options="all", batch_size=None):
        if result_options == "all":
            self.result_options = (
                self._onedal_incremental_basic_statistics.get_all_result_options()
            )
        else:
            self.result_options = result_options
        self._need_to_finalize = False
        self.batch_size = batch_size

    def _get_onedal_result_options(self, options):
        if isinstance(options, list):
            onedal_options = "|".join(self.result_options)
        else:
            onedal_options = options
        assert isinstance(onedal_options, str)
        return options

    @run_with_n_jobs
    def _onedal_finalize_fit(self):
        assert hasattr(self, "_onedal_estimator")
        self._onedal_estimator.finalize_fit()
        self._need_to_finalize = False

    @run_with_n_jobs
    def _onedal_partial_fit(self, X, weights, queue):
        onedal_params = {
            "result_option": self._get_onedal_result_options(self.result_options),
            "method": "by_default",
        }
        if not hasattr(self, "_onedal_estimator"):
            self._onedal_estimator = self._onedal_incremental_basic_statistics(
                **onedal_params
            )
        self._onedal_estimator.partial_fit(X, weights, queue)
        self._need_to_finalize = True

    def __getattr__(self, attr):
        result_options = self.__dict__["result_options"]
        is_statistic_attr = (
            isinstance(result_options, str) and (attr == result_options)
        ) or (isinstance(result_options, list) and (attr in result_options))
        if is_statistic_attr:
            if self._need_to_finalize:
                self._onedal_finalize_fit()
            return getattr(self._onedal_estimator, attr)
        if attr in self.__dict__:
            return self.__dict__[attr]

        raise AttributeError(
            f"'{self.__class__.__name__}' object has no attribute '{attr}'"
        )

    @support_usm_ndarray()
    def partial_fit(self, X, weights=None, queue=None):
        """Incremental fit with X. All of X is processed as a single batch.

        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
            Data for compute, where `n_samples` is the number of samples and
            `n_features` is the number of features.

        weights : array-like of shape (n_samples,)
            Weights for compute weighted statistics, where `n_samples` is the number of samples.

        Returns
        -------
        self : object
            Returns the instance itself.
        """
        X = check_array(X, dtype=[np.float64, np.float32])
        if weights is not None:
            weights = check_array(
                weights, dtype=[np.float64, np.float32], ensure_2d=False
            )
        self._onedal_partial_fit(X, weights, queue)
        return self

    def fit(self, X, weights=None, queue=None):
        """Compute statistics with X, using minibatches of size batch_size.

        Parameters
        ----------
        X : array-like of shape (n_samples, n_features)
            Data for compute, where `n_samples` is the number of samples and
            `n_features` is the number of features.

        weights : array-like of shape (n_samples,)
            Weights for compute weighted statistics, where `n_samples` is the number of samples.

        Returns
        -------
        self : object
            Returns the instance itself.
        """
        n_samples, n_features = X.shape
        if self.batch_size is None:
            batch_size_ = 5 * n_features
        else:
            batch_size_ = self.batch_size
        for batch in gen_batches(n_samples, batch_size_):
            X_batch = X[batch]
            if weights is not None:
                weights_batch = weights[batch]
                self.partial_fit(X_batch, weights_batch, queue=queue)
            else:
                self.partial_fit(X_batch, queue=queue)

        self._onedal_finalize_fit()
        return self