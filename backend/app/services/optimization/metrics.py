"""Benchmark metrics.

The optimisation objective uses the weighted sum-of-squared-differences DTSI
(see problem.py). For reporting and the NSGA-II-vs-LP benchmark, the cosine
distance between consecutive formulation vectors is also computed here. The two
measures answer different questions: the squared-difference DTSI is what the
algorithm minimises, while cosine distance is a scale-invariant descriptor of
how much the *shape* of the ration changed.
"""

from __future__ import annotations

import numpy as np


def cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """1 - cosine similarity between two proportion vectors (0 = identical)."""
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    sim = float(np.dot(a, b) / (na * nb))
    sim = max(-1.0, min(1.0, sim))
    return 1.0 - sim
