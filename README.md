# poultry-feed-formulation

This repository contains the source code for a dynamic, least-cost poultry feed formulation system designed for volatile market conditions in Sub-Saharan Africa, specifically Rwanda. 

Feed costs constitute up to 70% of poultry production expenses. In volatile environments, static formulations derived from stale price lists quickly become sub-optimal. This project implements a hybrid approach: a machine learning regression model forecasts next-period raw ingredient prices from historical World Food Programme (WFP) data, and a multi-objective evolutionary algorithm (NSGA-II) optimizes nutritional feed composition against those forecasted prices while maintaining recipe stability.

## System Architecture

The application is structured as a decoupled client-server architecture:

```
[ WFP Price Data ] --> [ ML Forecasting Service ] 
                             |
                             v
                       [ Predicted Prices ]
                             |
                             v
[ Flutter App ] <---> [ FastAPI Server ] <---> [ DEAP NSGA-II Optimizer ]
                             ^
                             v
                     [ PostgreSQL DB ]
```

1. [**Backend Service**](./backend/README.md): A FastAPI web service orchestrating database queries, running the SciPy Linear Programming (LP) baseline, executing the NSGA-II genetic algorithm, and managing the Scikit-learn Gradient Boosting price forecaster.
2. [**Mobile Client**](./mobile/README.md): A Flutter application that allows users to manage flocks, input local market prices, execute optimization runs, visualize price trajectories, and analyze cost vs. diet stability trade-offs.

---

## Machine Learning and Optimization Pipeline

### 1. Temporal Price Forecasting
The system trains a pooled `GradientBoostingRegressor` on historical return series derived from the World Food Programme retail and wholesale dataset for Rwanda.
*   **Target**: One-month-ahead log-returns of domestically traded commodities (`Maize`, `Cassava`, `Salt`, `Oil (palm)`, and `Fish (dry)`).
*   **Exogenous Inputs**: Imported ingredients (such as vitamin premixes and amino acids) without local pricing histories are priced via parity and entered manually.
*   **Validation**: Evaluated using walk-forward out-of-sample backtesting against naive random walk and seasonal naive benchmarks.

### 2. Multi-Objective Feed Formulation
Feed formulation is traditionally solved via Linear Programming (LP) to find the absolute least-cost vertex that meets nutritional constraints. However, small price movements in LP cause drastic shifts in recipe components, which can stress poultry digestive systems.

To solve this, the system uses NSGA-II (Non-dominated Sorting Genetic Algorithm II) to optimize two conflicting objectives:
1.  **Cost Minimization**: Minimizing the overall cost per kilogram of feed based on forecasted prices.
2.  **Diet Transition Stability Index (DTSI)**: Minimizing the cosine distance of the new formulation's ingredient vector relative to the flock's currently selected formulation.

---

## Repository Structure

```
.
├── backend/                  # FastAPI web server and ML pipeline
│   ├── app/
│   │   ├── api/              # API router and endpoints
│   │   ├── db/               # SQLAlchemy models and seed scripts
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic schemas
│   │   ├── services/
│   │   │   ├── forecasting/  # ML model training and inference
│   │   │   └── optimization/ # NSGA-II and LP solvers
│   │   └── data/             # Historical price datasets (WFP CSVs)
│   ├── alembic/              # Database migration history
|   └── docker-compose.yml        # Docker composition stack
├── mobile/                   # Flutter mobile client code
│   ├── lib/
│   │   ├── src/
│   │   │   ├── api/          # API client and repository
│   │   │   ├── models/       # Dart model classes
│   │   │   ├── screens/      # Application view controllers
│   │   │   └── widgets/      # Charts and UI elements
│   │   └── main.dart         # App entry point
└── notebook/                 # Jupyter notebooks for model validation
```

---

## Setup

To spin up the entire application stack, refer to the setup steps in the sub-project directories:

*   For database migrations, model seeding, and API configurations, see the [backend setup guide](./backend/README.md).
*   For running the mobile interface on emulators or physical devices, see the [mobile client setup guide](./mobile/README.md).

## Screenshots

### Backend Swagger UI

![swagger screenshot](./screenshots/swagger.png)

### Mobile Client UI

![login](./screenshots/login.png) ![price forecasts](./screenshots/price_forecasts.png) ![formulated ration](./screenshots/formulation%20_ration_details.png)