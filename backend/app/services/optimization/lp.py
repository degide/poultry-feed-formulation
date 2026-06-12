"""Linear-programming baseline.

Implements the classical single-objective least-cost formulation using
`scipy.optimize.linprog` (HiGHS solver). This is the benchmark against which
NSGA-II is evaluated for Objective 3. The LP minimises cost subject to the
sum-to-one mass balance, ingredient bounds, and the NRC nutrient constraints;
it has no notion of dietary continuity, so its DTSI is simply reported (not
optimised) for comparison on the same axes as the NSGA-II Pareto front.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import linprog

from app.services.optimization.problem import FeedFormulationProblem
from app.services.optimization.solution import Solution


def run_lp(problem: FeedFormulationProblem) -> Solution | None:
    n = problem.n
    c = problem.prices  # minimise cost

    a_ub: list[np.ndarray] = []
    b_ub: list[float] = []
    for con in problem.constraints:
        coeffs = problem.nutrient_coeffs.get(con.nutrient)
        if coeffs is None:
            continue
        if con.min_value is not None:
            # coeffs @ x >= min  ->  -coeffs @ x <= -min
            a_ub.append(-coeffs)
            b_ub.append(-con.min_value)
        if con.max_value is not None:
            a_ub.append(coeffs)
            b_ub.append(con.max_value)

    a_eq = np.ones((1, n))   # sum of fractions = 1
    b_eq = np.array([1.0])
    bounds = list(zip(problem.lower_bounds.tolist(), problem.upper_bounds.tolist()))

    res = linprog(
        c=c,
        A_ub=np.array(a_ub) if a_ub else None,
        b_ub=np.array(b_ub) if b_ub else None,
        A_eq=a_eq,
        b_eq=b_eq,
        bounds=bounds,
        method="highs",
    )

    if not res.success:
        return None

    x = problem.repair(res.x)
    return Solution(
        proportions=x,
        cost=problem.cost(x),
        dtsi=problem.dtsi(x),
        feasible=problem.is_feasible(x),
    )
