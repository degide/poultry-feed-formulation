"""Standalone test of the optimisation core (no DB).

Builds a layer-hen problem from the ingredient library with
representative Rwandan prices, runs the LP baseline and NSGA-II, and prints a
feasibility / Pareto-shape report.
"""

import time

import numpy as np

from app.services.optimization.builder import build_problem
from app.services.optimization.lp import run_lp
from app.services.optimization.metrics import cosine_distance
from app.services.optimization.nsga2 import run_nsga2
from app.services.optimization.nutrition import constraints_for_flock

# Table 3.1 values: name, category, {nutrient: value}
LIB = [
    ("Whole maize grain", "energy_source", [9.0, 3350, 2.5, 1.8, 0.02, 0.10, 2.2, 88]),
    ("Soybean meal (44%)", "protein_source", [44.0, 2240, 6.1, 1.4, 0.35, 0.25, 7.0, 89]),
    ("Sunflower seed cake", "protein_source", [28.0, 1900, 3.2, 1.9, 0.40, 0.30, 22.0, 90]),
    ("Fishmeal (65% CP)", "protein_source", [65.0, 2880, 5.0, 2.8, 5.50, 2.80, 1.0, 92]),
    ("Wheat bran", "energy_source", [15.5, 1500, 3.4, 1.5, 0.13, 0.15, 10.0, 88]),
    ("Cassava meal", "energy_source", [2.5, 3200, 1.5, 0.7, 0.10, 0.05, 3.5, 86]),
    ("Limestone", "mineral", [0.0, 0, 0.0, 0.0, 38.0, 0.00, 0.0, 100]),
    ("Dicalcium phosphate", "mineral", [0.0, 0, 0.0, 0.0, 22.0, 18.0, 0.0, 100]),
    ("Sodium chloride (salt)", "mineral", [0.0, 0, 0.0, 0.0, 0.0, 0.00, 0.0, 100]),
    ("Layer premix (vit/min)", "premix", [0.0, 0, 0.0, 0.0, 0.0, 0.00, 0.0, 100]),
    ("Crude palm oil", "fat", [0.0, 8800, 0.0, 0.0, 0.0, 0.00, 0.0, 100]),
    ("DL-Methionine", "additive", [58.0, 3500, 0.0, 100.0, 0.0, 0.00, 0.0, 100]),
]
NUTS = ["crude_protein", "metabolisable_energy", "lysine", "methionine",
        "calcium", "available_phosphorus", "crude_fibre", "dry_matter"]
PRICES_RWF = [450, 750, 500, 1400, 300, 350, 120, 900, 400, 2500, 2000, 6000]

ingredients = []
prices = {}
for idx, ((name, cat, vals), price) in enumerate(zip(LIB, PRICES_RWF), start=1):
    ingredients.append({
        "ingredient_id": idx,
        "name": name,
        "category": cat,
        "nutrients": dict(zip(NUTS, [float(v) for v in vals])),
    })
    prices[idx] = float(price)

constraints = constraints_for_flock("layer")
problem = build_problem(ingredients=ingredients, prices=prices, constraints=constraints)

print(f"Problem: n={problem.n} ingredients")
print(f"sum(lb)={problem.lower_bounds.sum():.4f}  sum(ub)={problem.upper_bounds.sum():.4f}\n")

# --- LP baseline ---
t0 = time.time()
lp = run_lp(problem)
lp_t = time.time() - t0
if lp is None:
    print("LP: INFEASIBLE — constraints/bounds need adjustment.")
else:
    print(f"LP baseline ({lp_t*1000:.0f} ms): cost={lp.cost:.2f} RWF/kg  "
          f"feasible={lp.feasible}")
    levels = problem.nutrient_levels(lp.proportions)
    print("  nutrient levels:", {k: round(v, 2) for k, v in levels.items() if k != 'dry_matter'})
    print("  top ingredients (%):")
    for name, p in sorted(zip(problem.ingredient_names, lp.proportions_percent()),
                          key=lambda x: -x[1])[:6]:
        print(f"    {name:24s} {p:6.2f}")

# Use the LP solution as the 'previous formulation' so DTSI is meaningful.
problem.previous_formulation = lp.proportions.copy() if lp else None

# --- NSGA-II (reduced gens for a fast smoke test) ---
t0 = time.time()
front = run_nsga2(problem, population_size=80, max_generations=120, seed=42)
ns_t = time.time() - t0
print(f"\nNSGA-II ({ns_t:.2f} s): {len(front)} feasible Pareto points")
if front:
    costs = [s.cost for s in front]
    dtsis = [s.dtsi for s in front]
    print(f"  cost range:  {min(costs):.2f} .. {max(costs):.2f} RWF/kg")
    print(f"  DTSI range:  {min(dtsis):.6f} .. {max(dtsis):.6f}")
    print("  sample front points (cost, dtsi, cosine_dist):")
    for s in front[:: max(1, len(front) // 6)][:6]:
        cd = cosine_distance(s.proportions, problem.previous_formulation)
        print(f"    cost={s.cost:8.2f}  dtsi={s.dtsi:.6f}  cos={cd:.5f}  "
              f"sum={s.proportions.sum():.4f}")
    # The cheapest NSGA-II point should be close to the LP optimum.
    print(f"\n  cheapest NSGA-II cost={min(costs):.2f} vs LP cost={lp.cost:.2f}  "
          f"(gap {100*(min(costs)-lp.cost)/lp.cost:+.2f}%)")
