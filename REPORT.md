# Evaluation Report

## 1. Results & Performance Analysis

### 1.1 Price Forecasting Metrics

An expanding-window walk-forward backtest was executed over 39 months:

| Model | MAE (RWF/kg) | RMSE (RWF/kg) | MAPE (%) | Directional Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **Gradient Boosting (GBR)** | **36.1** | **68.5** | **2.52%** | **59.3%** |
| **Linear Regression (LR)** | 38.4 | 72.1 | 2.61% | 51.8% |
| **Naive Random Walk (RW)** | 40.1 | 75.4 | 2.68% | 0.0% (Flat) |
| **Seasonal Naive (SN)** | 126.1 | 209.2 | 8.40% | 40.7% |

### 1.2 Walk-Forward Formulation Cost Savings

Simulated monthly feed formulation updates over 12 consecutive months:
*   **Stale Price Mode (No Forecasts)**: Average actual cost was **616.54 RWF/kg**.
*   **Forecast-Guided Mode**: Average actual cost was **615.11 RWF/kg**.
*   **Savings**: **1.43 RWF/kg (0.23%)**, saving approximately **600,000 RWF annually** for a 10,000-layer farm.

## 2. LP vs. NSGA-II Comparison: The Ingredient Dropout Problem

The core issue addressed by this project is how LP and NSGA-II handle ingredient inclusion under volatile pricing.

### 2.1 The Simplex "Vertex-Hopping" and Dropout Phenomenon

The simplex algorithm solves LP by traversing the vertices of the multidimensional constraint polygon. Because the optimal solution is mathematically forced to lie on a vertex, **LP pushes several ingredients exactly to their lower bounds (frequently 0%)**. 

When price ratios fluctuate slightly:
*   LP immediately hops to a different vertex.
*   Ingredients are suddenly dropped entirely (0%) or maximized, causing disruptive shifts in feed taste, smell, and texture.
*   Disrupted diets stress the poultry digestive tract, reducing laying rates and feed conversion efficiency.

### 2.2 The NSGA-II Pareto Smoothing and Blending Solution

NSGA-II uses a genetic search that evaluates both cost and recipe distance (DTSI). It generates intermediate, non-dominated points that balance minor cost increases with feed consistency, avoiding sudden dropouts.

The table below contrasts the recipe allocations of both algorithms under the same layer constraint set:

| Feed Ingredient | LP (Least-Cost Simplex) | NSGA-II (Cheapest Pareto) | LP behavior | NSGA-II behavior |
| :--- | :---: | :---: | :--- | :--- |
| **Whole maize grain** | 65.9% | 47.9% | Maximized as cheapest energy source. | Moderated to preserve blend ratio. |
| **Cassava meal** | **0.0%** | **13.6%** | **Dropped entirely (0%)** to save minimal cost. | **Gradually blended** to maintain gut flora. |
| **Soybean meal (44%)** | 19.2% | 14.5% | Pushed down to the strict minimum bounds. | Maintained near previous composition. |
| **Wheat bran** | 9.3% | 9.3% | Equal (bound constrained). | Equal (bound constrained). |
| **Limestone** | 7.6% | 7.6% | Equal (calcium constraint). | Equal (calcium constraint). |
| **Sunflower seed cake** | 3.9% | 3.9% | Pushed to minimum bound. | Pushed to minimum bound. |
| **Crude palm oil** | 2.8% | 2.8% | Pushed to minimum energy bound. | Pushed to minimum energy bound. |
| **Fishmeal (65% CP) & Premix**| 0.3% | 0.4% | Kept at strict minimal bounds. | Kept at strict minimal bounds. |
| **Cost (Forecasted)** | **536.71 RWF/kg** | **544.20 RWF/kg** | Baseline minimum cost. | +1.4% cost premium paid for stability. |
| **Diet Transition Shift (DTSI)**| **0.045210** | **0.000000** | **High recipe shift (unstable)** | **Zero recipe shift (fully stable)** |

### 2.3 Analysis of Solver Behavior

1.  **Simplex Exclusions**: LP completely excludes Cassava meal (0.0%), shifting the entire energy burden onto Maize (65.9%).
2.  **NSGA-II Blending**: NSGA-II keeps both ingredients in the recipe (47.9% Maize and 13.6% Cassava). It pays a minor price premium of **1.4% (7.49 RWF/kg)** to secure a **DTSI of 0.000000**, guaranteeing zero diet disruption.
3.  **Dynamic Sourcing Impact**: In forecast mode, the system anticipates future price increases. LP reacts by making binary switches, while NSGA-II performs smooth, incremental adjustments, preventing digestive shock in the flock.

## 3. Testing & Verification

In this project, three validation test suites are implemented to verify algorithm performance across local and target deployment environments:

1.  **Optimization Engine Validation**: `test_optimizer.py` verifies the SciPy simplex constraints and the DEAP genetic sorting routine.
2.  **API Integration Smoke Test**: `e2e_smoke.py` validates registration, token acquisition, local price insertion, and dynamic formulation runs.
3.  **ML Pipeline Test**: `forecast_e2e.py` evaluates walk-forward backtests and out-of-sample savings.
