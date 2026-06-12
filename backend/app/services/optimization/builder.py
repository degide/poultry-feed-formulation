"""Build a FeedFormulationProblem from database rows.

Ingredient inclusion bounds and DTSI biological-sensitivity weights are not part
of the relational schema, so sensible defaults are defined here 
(e.g. salt 0.2-0.5%, premix 0.25-0.50%, maize 0-70%; energy and
protein sources carry higher DTSI weights than minerals/additives).
"""

from __future__ import annotations

import numpy as np

from app.services.optimization.nutrition import (
    CRUDE_PROTEIN,
    NutrientConstraint,
    diet_coefficient,
)
from app.services.optimization.problem import FeedFormulationProblem

# Per-ingredient inclusion bounds as fractions of the total ration.
DEFAULT_BOUNDS: dict[str, tuple[float, float]] = {
    "Whole maize grain": (0.0, 0.70),
    "Soybean meal (44%)": (0.0, 0.40),
    "Sunflower seed cake": (0.0, 0.15),
    "Fishmeal (65% CP)": (0.0, 0.10),
    "Wheat bran": (0.0, 0.20),
    "Cassava meal": (0.0, 0.30),
    "Limestone": (0.0, 0.12),
    "Dicalcium phosphate": (0.0, 0.03),
    "Sodium chloride (salt)": (0.002, 0.005),
    "Layer premix (vit/min)": (0.0025, 0.005),
    "Crude palm oil": (0.0, 0.06),
    "DL-Methionine": (0.0, 0.005),
}
_FALLBACK_BOUNDS = (0.0, 0.50)

# DTSI sensitivity weights by ingredient category.
CATEGORY_DTSI_WEIGHT: dict[str, float] = {
    "energy_source": 1.0,
    "protein_source": 1.0,
    "fat": 0.5,
    "mineral": 0.2,
    "premix": 0.1,
    "additive": 0.1,
}
_FALLBACK_DTSI_WEIGHT = 0.5


def build_problem(
    *,
    ingredients: list[dict],
    prices: dict[int, float],
    constraints: list[NutrientConstraint],
    previous_formulation: dict[int, float] | None = None,
    penalty_coefficient: float = 1_000_000.0,
) -> FeedFormulationProblem:
    """Assemble the optimisation problem.

    Args:
        ingredients: list of dicts with keys
            ``ingredient_id``, ``name``, ``category``, ``nutrients`` (a mapping
            of nutrient_type -> value).
        prices: ingredient_id -> price per kg (RWF). Ingredients without a price
            are excluded.
        constraints: active NRC nutrient constraints.
        previous_formulation: ingredient_id -> fraction (the active ration), or
            None for a first-time formulation.
    """
    usable = [ing for ing in ingredients if ing["ingredient_id"] in prices]
    if not usable:
        raise ValueError("No ingredients with a known market price were provided.")

    ids = [ing["ingredient_id"] for ing in usable]
    names = [ing["name"] for ing in usable]
    n = len(usable)

    price_vec = np.array([prices[i] for i in ids], dtype=float)

    lb = np.empty(n)
    ub = np.empty(n)
    dtsi_w = np.empty(n)
    for k, ing in enumerate(usable):
        low, high = DEFAULT_BOUNDS.get(ing["name"], _FALLBACK_BOUNDS)
        lb[k], ub[k] = low, high
        dtsi_w[k] = CATEGORY_DTSI_WEIGHT.get(ing["category"], _FALLBACK_DTSI_WEIGHT)

    # Build linear nutrient coefficients (with amino-acid CP conversion).
    nutrient_types: set[str] = set()
    for ing in usable:
        nutrient_types.update(ing["nutrients"].keys())

    nutrient_coeffs: dict[str, np.ndarray] = {}
    for nutrient in nutrient_types:
        vec = np.zeros(n)
        for k, ing in enumerate(usable):
            raw = ing["nutrients"].get(nutrient)
            if raw is None:
                continue
            cp = ing["nutrients"].get(CRUDE_PROTEIN, 0.0)
            vec[k] = diet_coefficient(nutrient, raw, cp)
        nutrient_coeffs[nutrient] = vec

    prev_vec: np.ndarray | None = None
    if previous_formulation:
        prev_vec = np.array(
            [previous_formulation.get(i, 0.0) for i in ids], dtype=float
        )

    return FeedFormulationProblem(
        ingredient_ids=ids,
        ingredient_names=names,
        prices=price_vec,
        lower_bounds=lb,
        upper_bounds=ub,
        nutrient_coeffs=nutrient_coeffs,
        constraints=constraints,
        dtsi_weights=dtsi_w,
        previous_formulation=prev_vec,
        penalty_coefficient=penalty_coefficient,
    )
