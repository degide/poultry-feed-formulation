"""Common solution container returned by both optimisers."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Solution:
    proportions: np.ndarray  # fractions summing to ~1, shape (n,)
    cost: float              # RWF/kg
    dtsi: float              # weighted squared-difference DTSI (objective f2)
    feasible: bool

    def proportions_percent(self) -> np.ndarray:
        return self.proportions * 100.0
