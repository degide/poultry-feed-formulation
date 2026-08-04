# Dynamic Least-Cost Poultry Feed Formulation under Sub-Saharan Market Volatility

[![API Documentation](https://img.shields.io/badge/API_Docs-FastAPI_Swagger-009688?style=flat-square&logo=fastapi)](http://portstead.com:8000/docs)
[![Android APK](https://img.shields.io/badge/Mobile_App-Android_APK-3DDC84?style=flat-square&logo=android)](https://github.com/degide/poultry-feed-formulation/releases/download/v1.0.0-alpha/feed_formulation_release.apk)
[![Video Demo](https://img.shields.io/badge/Video_Defense-Watch_Demo-FF0000?style=flat-square&logo=youtube)](https://www.bugufi.link/8z-tu2)
[![License](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](./LICENSE)

A cross-platform software engineering system that integrates a machine learning price forecasting engine (**Gradient Boosting Regressor**) with a multi-objective evolutionary algorithm (**NSGA-II**) to optimize poultry feed formulations under Sub-Saharan market volatility. 

The system resolves the traditional **Linear Programming (LP) "vertex-hopping" phenomenon**, where minor market price shifts cause sudden ingredient dropouts and abrupt diet changes that induce gut stress and egg-laying drops in poultry flocks, by optimizing both ration cost and **Diet Transition Stability (DTSI)**.

## Key Deliverables & Quick Links

*   **Live Swagger API Documentation:** [`http://portstead.com:8000/docs`](http://portstead.com:8000/docs)
*   **Android Application Binary (APK):** [`feed_formulation_release.apk`](https://github.com/degide/poultry-feed-formulation/releases/download/v1.0.0-alpha/feed_formulation_release.apk)
*   **System Video Defense & Demo:** [`https://www.bugufi.link/8z-tu2`](https://www.bugufi.link/8z-tu2)
*   **Jupyter Model Development Notebook:** [`notebook/ModelNotebook.ipynb`](./notebook/ModelNotebook.ipynb)
*   **Empirical Evaluation & Performance Report:** [`REPORT.md`](./REPORT.md)
*   **Production Deployment & Server Infrastructure Guide:** [`DEPLOYMENT.md`](./DEPLOYMENT.md)
*   **UML System Diagrams Specification:** [`docs/uml`](./docs/uml/)

## System Architecture

The application adopts a decoupled, multi-tier client-server architecture:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                 Presentation Layer (Cross-Platform Mobile)              │
│       Flutter Mobile Client (Dart)  <--->  SQLite Offline Cache         │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTPS / TLS 1.3 (JSON REST API)
┌────────────────────────────────────▼────────────────────────────────────┐
│                  Application Gateway & Security Layer                   │
│       FastAPI Web Server (Python 3.12)  |  JWT Auth & Bcrypt Hashing    │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Internal Service Calls
┌────────────────────────────────────▼────────────────────────────────────┐
│              Analytics & Optimization Intelligence Core                 │
│  • ML Forecaster: Scikit-learn Gradient Boosting Regressor (Log-Returns)│
│  • Pareto Evolutionary Solver: DEAP NSGA-II (Dual Objective $f_1, f_2$) │
│  • LP Baseline Solver: SciPy linprog (HiGHS Simplex Engine)             │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ Async SQLAlchemy / AsyncPG
┌────────────────────────────────────▼────────────────────────────────────┐
│                         Data Persistence Layer                          │
│       PostgreSQL Relational DB  |  WFP & RAB Historical Datasets        │
└─────────────────────────────────────────────────────────────────────────┘
```

1.  **Backend Web Gateway & Optimization Service (`backend/`)**: Built with **FastAPI** and **Python 3.12**, managing database ORM persistence via **PostgreSQL**, executing the **SciPy `linprog`** LP baseline, running the **DEAP NSGA-II** evolutionary solver, and orchestrating the **Scikit-learn** Gradient Boosting price forecaster.
2.  **Cross-Platform Client Application (`mobile/`)**: Built with **Flutter**, providing flock management, local market price entry, asynchronous optimization job execution, interactive Pareto front visualization, and offline data persistence via SQLite.

## Mathematical Formulations & Optimization Mechanics

### 1. Dual-Objective Pareto Formulation (NSGA-II)
Traditional feed formulation uses Linear Programming (LP) to minimize cost alone ($f_1$), which pushes ingredient proportions to constraint polygon vertices (often 0%). Slight price variations cause binary ingredient swaps. NSGA-II solves a bi-objective trade-off problem:

$$\min_{\mathbf{x} \in \mathcal{S}} \mathbf{F}(\mathbf{x}) = \left[ f_1(\mathbf{x}),\, f_2(\mathbf{x}) \right]^T$$

*   **Objective 1: Total Ration Cost ($f_1$)**  
    $$f_1(\mathbf{x}) = \sum_{i=1}^{n} x_i \cdot \hat{p}_i$$
    where $x_i$ is the weight fraction of ingredient $i$, and $\hat{p}_i$ is the observed or ML-forecasted retail price per kg in RWF.

*   **Objective 2: Diet Transition Stability Index ($f_2$ / DTSI)**
    $$f_2(\mathbf{x}) = 1 - \frac{\mathbf{x} \cdot \mathbf{x}^{\text{active}}}{\|\mathbf{x}\|_2 \|\mathbf{x}^{\text{active}}\|_2}$$
    where $f_2(\mathbf{x})$ measures the cosine distance relative to the flock's active ration vector $\mathbf{x}^{\text{active}}$. Minimizing DTSI prevents sudden shifts in feed taste, texture, and microbial flora impact.

*   **Feasible Region Constraints ($\mathcal{S}$)**  

    $$\sum_{i=1}^{n} x_i = 1, \qquad L_i \le x_i \le U_i \quad \forall i$$

    $$\mathbf{A}_{\text{nutrients}} \cdot \mathbf{x} \ge \mathbf{b}_{\text{NRC(1994)}}$$

    Enforces exact nutritional bounds for Crude Protein, Metabolizable Energy, Lysine, Methionine, Calcium, Available Phosphorus, Crude Fibre, and Dry Matter based on National Research Council (1994) poultry standards.

### 2. Price Forecasting Pipeline (GBR)
*   **Target Variable**: One-month-ahead log-return $r_{i,t} = \ln\left(P_{i,t} / P_{i,t-1}\right)$ derived from 39+ months of World Food Programme (WFP) and Rwanda Agriculture Board (RAB) retail data. Log-differencing ensures stationarity.
*   **Feature Matrix**: 1, 2, and 3-month return lags ($r_{t-1}, r_{t-2}, r_{t-3}$), 3-month rolling return mean ($\bar{r}_3$), rolling volatility ($\sigma_3$), harmonic seasonal sine/cosine terms ($\sin\frac{2\pi m}{12}, \cos\frac{2\pi m}{12}$), and categorical ingredient indicators.
*   **Nominal Price Reconstruction**:  
    $$\hat{P}_{i,t+1} = P_{i,t} \cdot \exp(\hat{r}_{i,t+1})$$

## Empirical Benchmark Highlights

From the walk-forward validation and backtesting suite documented in [`REPORT.md`](./REPORT.md):

### 1. Price Forecasting Evaluation (39-Month Walk-Forward)
| Model | MAE (RWF/kg) | RMSE (RWF/kg) | MAPE (%) | Directional Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **Gradient Boosting (GBR)** | **36.1** | **68.5** | **2.52%** | **59.3%** |
| **Linear Regression (LR)** | 38.4 | 72.1 | 2.61% | 51.8% |
| **Naive Random Walk (RW)** | 40.1 | 75.4 | 2.68% | 0.0% (Flat) |
| **Seasonal Naive (SN)** | 126.1 | 209.2 | 8.40% | 40.7% |

### 2. LP Vertex-Hopping vs. NSGA-II Pareto Blending Comparison
Under identical pricing and layer-hen nutritional constraints:

| Ingredient | LP (Simplex Vertex) | NSGA-II (Cheapest Pareto) | LP Behavior | NSGA-II Behavior |
| :--- | :---: | :---: | :--- | :--- |
| **Whole maize grain** | 65.9% | 47.9% | Maximized as sole energy source | Moderated to preserve ratio |
| **Cassava meal** | **0.0%** | **13.6%** | **Dropped completely (0.0%)** | **Smoothly blended** |
| **Soybean meal (44%)** | 19.2% | 14.5% | Pushed to strict lower bound | Retained near active composition |
| **Forecast Cost** | **536.71 RWF/kg** | **544.20 RWF/kg** | Absolute minimum cost | +1.4% cost premium paid for stability |
| **Diet Shift (DTSI)** | **0.045210** | **0.000000** | **High recipe shock** | **Zero diet shock** |

---

## Repository Structure

```
poultry-feed-formulation/
├── backend/                      # Python FastAPI web server & ML optimization core
│   ├── app/
│   │   ├── api/                  # REST API routers (auth, flocks, ingredients, formulations)
│   │   ├── core/                 # App configuration & security settings
│   │   ├── db/                   # Database session, base class, & seed scripts
│   │   ├── models/               # SQLAlchemy ORM models (User, Flock, Formulation, etc.)
│   │   ├── schemas/              # Pydantic validation schemas
│   │   ├── services/             # Domain logic:
│   │   │   ├── forecasting/      # GBR log-return training, feature extraction, backtests
│   │   │   └── optimization/     # DEAP NSGA-II solver, SciPy LP engine, NRC bounds
│   │   └── data/                 # Raw WFP/RAB historical price CSV datasets
│   ├── alembic/                  # Database migration scripts
│   ├── test_optimizer.py         # Standalone optimization engine validation script
│   ├── e2e_smoke.py              # Full REST API end-to-end integration test
│   ├── forecast_e2e.py           # Forecaster walk-forward validation script
│   ├── generate_plantuml.py      # PlantUML diagram generator utility
│   └── docker-compose.yml        # Docker service orchestration configuration
├── mobile/                       # Cross-platform Flutter mobile client
│   ├── lib/
│   │   ├── src/
│   │   │   ├── api/              # HTTP REST repository & API client
│   │   │   ├── models/           # Typed Dart models
│   │   │   ├── screens/          # Views (Login, Account, Flocks, Formulate, Result, Legal)
│   │   │   └── widgets/          # Custom Pareto chart, location selector, cards, pills
│   │   └── main.dart             # Application root entry point
│   └── pubspec.yaml              # Flutter project dependencies
├── notebook/                     # Jupyter notebooks for model validation
│   └── ModelNotebook.ipynb       # Model training, feature analysis, and backtesting
├── docs/                         # PlantUML & Mermaid UML architecture diagrams
├── apk/                          # Compiled Android application binaries
├── REPORT.md                     # Empirical evaluation and performance report
├── DEPLOYMENT.md                 # Production deployment and server setup guide
└── LICENSE                       # MIT Open Source License
```

## Local Setup & Quick Start Guide

### Prerequisites
*   **Python 3.12+**
*   **Flutter SDK 3.19+**
*   **PostgreSQL 15+**

### 1. Backend Service Setup

```bash
# Clone the repository
git clone https://github.com/degide/poultry-feed-formulation.git
cd poultry-feed-formulation/backend

# Create and activate virtual environment
python3 -m venv ../venv
source ../venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Execute database migrations & seed initial ingredient/price data
alembic upgrade head
python -m app.db.seed

# Start local FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Access the interactive API documentation at `http://localhost:8000/docs`.

### 2. Running Verification & Test Suites

The codebase includes three standalone test suites verifying core system components:

```bash
# 1. Validate optimization solvers (SciPy LP vs DEAP NSGA-II)
python test_optimizer.py

# 2. Validate GBR price forecaster & walk-forward backtest
python forecast_e2e.py

# 3. Validate full REST API end-to-end integration
python e2e_smoke.py
```

### 3. Model Development Notebook

```bash
pip install -r notebook/requirements.txt
jupyter notebook notebook/ModelNotebook.ipynb
```

### 4. Mobile Client Setup (Flutter)

```bash
cd ../mobile

# Fetch Flutter packages
flutter pub get

# Run on Chrome for web testing
flutter run -d chrome

# Build release Android APK
flutter build apk --release
```

## Screenshots

### 1. Interactive OpenAPI / Swagger Documentation
![Swagger Interface](./screenshots/swagger.png)

### 2. Flutter Mobile Application
<p float="left">
  <img src="./screenshots/login.png" width="30%" alt="Login Screen" />
  <img src="./screenshots/price_forecasts.png" width="30%" alt="Price Forecasts" />
  <img src="./screenshots/formulation _ration_details.png" width="30%" alt="Ration Details" />
</p>

## License

Distributed under the MIT License. See [LICENSE](./LICENSE) for more information.
