"""Nutritional constraints and nutrient-coefficient construction.

Default minimum/maximum nutrient targets are based on NRC (1994) for laying
hens and broilers. All values are configurable; these are sensible defaults
for a general layer/broiler grower ration. Amino-acid values in the ingredient 
library are stored as a percentage of crude protein, so this module converts 
them to a percentage of the diet when building the linear nutrient coefficients.
"""

from __future__ import annotations

from dataclasses import dataclass

# Nutrient keys used throughout the optimiser.
CRUDE_PROTEIN = "crude_protein"
ME = "metabolisable_energy"
LYSINE = "lysine"
METHIONINE = "methionine"
CALCIUM = "calcium"
AVAIL_P = "available_phosphorus"
CRUDE_FIBRE = "crude_fibre"
DRY_MATTER = "dry_matter"

# Amino acids stored as % of crude protein -> need CP conversion.
AMINO_ACIDS_AS_PCT_CP = {LYSINE, METHIONINE}


@dataclass(frozen=True)
class NutrientConstraint:
    nutrient: str
    min_value: float | None = None
    max_value: float | None = None


# (NRC 1994 derived defaults; all configurable per proposal section 1.5)
DEFAULT_CONSTRAINTS: dict[str, list[NutrientConstraint]] = {
    "layer": [
        NutrientConstraint(CRUDE_PROTEIN, min_value=16.0),
        NutrientConstraint(ME, min_value=2750.0, max_value=2950.0),
        NutrientConstraint(LYSINE, min_value=0.69),
        NutrientConstraint(METHIONINE, min_value=0.30),
        NutrientConstraint(CALCIUM, min_value=3.25, max_value=4.50),
        NutrientConstraint(AVAIL_P, min_value=0.30, max_value=0.60),
        NutrientConstraint(CRUDE_FIBRE, max_value=7.0),
    ],
    "broiler": [
        NutrientConstraint(CRUDE_PROTEIN, min_value=19.0),
        NutrientConstraint(ME, min_value=2900.0, max_value=3200.0),
        NutrientConstraint(LYSINE, min_value=1.00),
        NutrientConstraint(METHIONINE, min_value=0.45),
        NutrientConstraint(CALCIUM, min_value=0.90, max_value=1.20),
        NutrientConstraint(AVAIL_P, min_value=0.40, max_value=0.55),
        NutrientConstraint(CRUDE_FIBRE, max_value=5.0),
    ],
}


def constraints_for_flock(flock_type: str) -> list[NutrientConstraint]:
    return DEFAULT_CONSTRAINTS.get(flock_type, DEFAULT_CONSTRAINTS["layer"])


def diet_coefficient(nutrient: str, raw_value: float, crude_protein: float) -> float:
    """Convert a stored ingredient nutrient value into a per-fraction diet coefficient.

    For most nutrients the stored value already represents % (or kcal/kg) of the
    ingredient, so the coefficient equals the value. For amino acids stored as
    % of crude protein, the diet contribution is `CP% * (aa_%CP / 100)`.
    """
    if nutrient in AMINO_ACIDS_AS_PCT_CP:
        return crude_protein * raw_value / 100.0
    return raw_value
