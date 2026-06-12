"""The feed-formulation optimisation problem.

Decision variables are ingredient proportions expressed as fractions that sum
to 1. Two objectives are minimised:

* f1 = total ration cost per kg  = sum_i (x_i * price_i)
* f2 = DTSI                       = sum_i (w_i * (x_i - x_prev_i)^2)

Nutritional feasibility (NRC targets) is enforced with a penalty function: 
each violation adds `penalty_coefficient * violation` to *both*
objectives, keeping infeasible solutions off the Pareto front. A `repair`
routine projects any candidate back onto the bounded simplex (genes within
[lb_i, ub_i], summing to 1).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.services.optimization.nutrition import NutrientConstraint


@dataclass
class FeedFormulationProblem:
    ingredient_ids: list[int]
    ingredient_names: list[str]
    prices: np.ndarray                       # shape (n,), RWF/kg
    lower_bounds: np.ndarray                 # shape (n,), fractions
    upper_bounds: np.ndarray                 # shape (n,), fractions
    nutrient_coeffs: dict[str, np.ndarray]   # nutrient -> coeffs, shape (n,)
    constraints: list[NutrientConstraint]
    dtsi_weights: np.ndarray                 # shape (n,)
    previous_formulation: np.ndarray | None = None  # shape (n,), fractions
    penalty_coefficient: float = 1_000_000.0

    @property
    def n(self) -> int:
        return len(self.ingredient_ids)

    # --- objectives -------------------------------------------------------
    def cost(self, x: np.ndarray) -> float:
        return float(self.prices @ x)

    def dtsi(self, x: np.ndarray) -> float:
        if self.previous_formulation is None:
            return 0.0
        diff = x - self.previous_formulation
        return float(self.dtsi_weights @ (diff * diff))

    def nutrient_levels(self, x: np.ndarray) -> dict[str, float]:
        return {n: float(c @ x) for n, c in self.nutrient_coeffs.items()}

    # --- constraints ------------------------------------------------------
    def constraint_violation(self, x: np.ndarray) -> float:
        """Total magnitude of NRC constraint violations (0.0 if feasible)."""
        total = 0.0
        levels = self.nutrient_levels(x)
        for c in self.constraints:
            level = levels.get(c.nutrient)
            if level is None:
                continue
            if c.min_value is not None and level < c.min_value:
                total += c.min_value - level
            if c.max_value is not None and level > c.max_value:
                total += level - c.max_value
        return total

    def is_feasible(self, x: np.ndarray, tol: float = 1e-6) -> bool:
        return self.constraint_violation(x) <= tol

    def evaluate(self, x: np.ndarray) -> tuple[float, float]:
        """Penalised (cost, dtsi) tuple used as the NSGA-II fitness."""
        penalty = self.penalty_coefficient * self.constraint_violation(x)
        return self.cost(x) + penalty, self.dtsi(x) + penalty

    # --- feasibility repair ----------------------------------------------
    def repair(self, x: np.ndarray, max_iter: int = 50) -> np.ndarray:
        """Project x onto {lb <= x <= ub, sum(x) = 1} by clip + redistribute."""
        x = np.clip(np.asarray(x, dtype=float), self.lower_bounds, self.upper_bounds)
        for _ in range(max_iter):
            s = x.sum()
            diff = 1.0 - s
            if abs(diff) < 1e-9:
                break
            if diff > 0:                       # need to add mass
                room = self.upper_bounds - x
            else:                              # need to remove mass
                room = x - self.lower_bounds
            total_room = room.sum()
            if total_room < 1e-12:
                break
            x = x + diff * (room / total_room)
            x = np.clip(x, self.lower_bounds, self.upper_bounds)
        return x
