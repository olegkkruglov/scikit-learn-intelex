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

import dpctl
import numpy as np

from sklearnex.basic_statistics import IncrementalBasicStatistics

incbs = IncrementalBasicStatistics(result_options=["mean", "max", "sum"])

# We do partial_fit for each batch and then print final result.
X_1 = np.array([[0, 1], [0, 1]])
result = incbs.partial_fit(X_1)

X_2 = np.array([[1, 2]])
result = incbs.partial_fit(X_2)

X_3 = np.array([[1, 1], [1, 2], [2, 3]])
result = incbs.partial_fit(X_3)

print(f"Mean:\n{result.mean}")
print(f"Max:\n{result.max}")
print(f"Sum:\n{result.sum}")

# We put the whole data to fit method, it is split automatically and then
# partial_fit is called for each batch.
incbs = IncrementalBasicStatistics(result_options=["mean", "max", "sum"], batch_size=3)
X = np.array([[0, 1], [0, 1], [1, 2], [1, 1], [1, 2], [2, 3]])
result = incbs.fit(X)

print(f"Mean:\n{result.mean}")
print(f"Max:\n{result.max}")
print(f"Sum:\n{result.sum}")
