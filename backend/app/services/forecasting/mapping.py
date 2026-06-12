"""WFP commodity -> feed-ingredient mapping.

Only domestically-traded ingredients appear in the WFP retail price database
and are therefore forecastable from it. Imported feed inputs (soybean meal,
premix, DL-methionine, dicalcium phosphate, sunflower cake, wheat bran) are
priced by import parity and are left on manually-entered prices. See the
forecasting methodology note in the docs.
"""

from __future__ import annotations

# our seed-library ingredient name -> WFP commodity name
INGREDIENT_TO_WFP: dict[str, str] = {
    "Whole maize grain": "Maize",
    "Cassava meal": "Cassava",
    "Sodium chloride (salt)": "Salt",
    "Crude palm oil": "Oil (palm)",
    "Fishmeal (65% CP)": "Fish (dry)",
}

FORECASTABLE_INGREDIENT_NAMES = set(INGREDIENT_TO_WFP)

# Palm oil is quoted per litre in WFP; convert to per-kg with this density.
PALM_OIL_DENSITY_KG_PER_L = 0.91
