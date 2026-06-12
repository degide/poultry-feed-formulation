# poultry-feed-formulation

Least-cost poultry feed formulation for Sub-saharan (especially Rwandan) conditions, where ingredient prices move around a lot and a ration that was cheapest last month often isn't cheapest this month. The system pairs a price-forecasting model with a multi-objective optimiser: a gradient-boosting model predicts next month's ingredient prices from WFP market data, and NSGA-II then searches for the cheapest nutritionally-adequate ration *against those forecasts* instead of against stale prices.

**Repository:** `https://github.com/degide/poultry-feed-formulation`

---

## ML Application

Formulation itself is an optimisation problem, not a learning problem. So the learning component sits *upstream* of the optimiser:

```
WFP price history --> gradient-boosting forecaster --> next-month prices --> NSGA-II cost objective
```

The forecaster only handles the five ingredients that are actually traded on local markets and show up in the WFP data (maize, cassava, salt, palm oil, dried fish). The imported inputs (soybean meal, premix, DL-methionine, dicalcium phosphate, etc.) are priced by import parity, have no local price series, and stay on manually-entered prices. They are treated as exogenous and say so rather than pretend to forecast something we have no data for.

## Model Notebook

[`ModelNotebook.ipynb`](notebook/ModelNotebook.ipynb) is the IPYTHON notebook for building and testing the model. It imports the *same* forecasting code the API runs (`app.services.forecasting`),
so the notebook and the deployed model can't drift apart. It covers:

- **Data visualization & engineering**: price trajectories, log-return distributions, volatility ranking, a cross-ingredient return correlation heatmap, a seasonality check, and the engineered feature matrix.

- **Architecture**: a `GradientBoostingRegressor` (an additive ensemble of depth-2 trees, learning-rate shrinkage, stochastic subsampling) trained on a *pooled* design matrix targeting monthly log-returns.

- **Metrics**: expanding-window walk-forward backtest reporting MAE / RMSE / MAPE against random-walk and seasonal-naive baselines, plus R^2 and a directional-accuracy figure (the closest classification-style analogue for a price regressor).

It's self-contained: it trains on the bundled CSV and needs no database or running server.

```bash
pip install -r backend/requirements.txt -r notebook/requirements.txt
jupyter notebook notebook/ModelNotebook.ipynb
```

## Stack

| Layer | Choice |
|-------|--------|
| API | FastAPI on Uvicorn (async) |
| Optimisation | DEAP (NSGA-II) + SciPy `linprog` HiGHS as an LP benchmark |
| Forecasting | scikit-learn gradient boosting, pandas |
| Data | PostgreSQL 16, SQLAlchemy 2.0 (async), Alembic |
| Auth | OAuth2 password flow, JWT, bcrypt |

Python 3.12+.

## Project layout

```
backend/
  app/
    api/routes/        # auth, ingredients, market-prices, flocks, forecasts, formulations
    services/
      optimization/    # NSGA-II engine, LP baseline, nutrition constraints, metrics
      forecasting/     # the ML: core model, DB service, WFP->ingredient mapping
    models/            # SQLAlchemy tables
    schemas/           # Pydantic request/response models
    db/                # async session, ingredient seed, price-history seed
    data/              # bundled Rwanda monthly price history (CSV)
  alembic/             # two migrations: initial schema + forecast columns
  e2e_smoke.py         # full HTTP journey against a running server
  forecast_e2e.py      # forecasting + forecast-mode formulation flow
  test_optimizer.py    # optimisation core, no server needed
docs/
  openapi.json         # exported API contract
  figures/             # data visualizations PNGs from the notebook
notebook/
  ModelNotebook.ipynb  # IPYNB model notebook
docker-compose.yml
```

## Getting started

You need either Docker, or local Python 3.11+ with a PostgreSQL 16 instance you
can reach.

### Docker (recommended)

```bash
cp backend/.env.example backend/.env     # set SECRET_KEY
docker compose up --build
```

Migrations run on container start. Seed the reference data once the stack is up:

```bash
docker compose exec backend python -m app.db.seed_ingredients
docker compose exec backend python -m app.db.seed_price_history
```

API: http://localhost:8000 · Swagger UI: http://localhost:8000/docs

### Local Python

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: POSTGRES_HOST/PORT/USER/PASSWORD/DB to match your Postgres,
# and set SECRET_KEY  (openssl rand -hex 32)

alembic upgrade head                  # initial schema + forecast columns
python -m app.db.seed_ingredients     # 12-ingredient library
python -m app.db.seed_price_history   # 136 monthly WFP price rows (5 ingredients, 2024-01..2026-05)

uvicorn app.main:app --reload
```

Seed order matters: ingredients first, because the price seeder resolves
ingredient IDs by name. Both seeders are idempotent, so re-running them won't
duplicate rows.

One gotcha worth flagging: `alembic upgrade head` and both seeders read the DB
connection from `.env`, so Postgres has to be running *before* you run them or
the commands just hang on the connection. If you don't want to manage a local
Postgres, use the Docker path.

### Sanity-check it works

With the server up and the data seeded:

```bash
python e2e_smoke.py        # register -> login -> prices -> generate -> poll -> select -> export
python forecast_e2e.py     # trains the model, runs the backtest, then formulates in
                           # both "latest" and "forecast" price modes and compares cost
```

`test_optimizer.py` exercises the NSGA-II/LP core directly and doesn't need a
server.

## API reference

The live Swagger UI is at `/docs` (and ReDoc at `/redoc`), generated from the code automatically. The exported contract is committed at [`docs/openapi.json`](docs/openapi.json). Import straight into Postman or view it in any OpenAPI viewer without running anything.

Quick map if you're navigating the UI: `auth` (register/login/me) -> `ingredients`
and `market-prices` (reference data) -> `flocks` (the birds you're feeding) ->
`forecasts` (train + inspect the model, run the backtest) -> `formulations`
(generate a ration, poll the job, view/select/export the result). Almost
everything needs a Bearer token: log in, copy the token, hit **Authorize**.

## Designs / interfaces

For now, the working interface is the API Swagger UI and the model notebook.

Data visualisations produced by the notebook live in [`docs/figures/`](docs/figures):

| File | Visualization |
|------|---------------|
| `fig1_price_series.png` | Monthly price per ingredient, 2024–2026 |
| `fig2_returns_volatility.png` | Log-return distribution and volatility ranking |
| `fig3_return_correlation.png` | How ingredient prices co-move |
| `fig4_seasonality.png` | Average return by calendar month |
| `fig5_feature_importance.png` | What the model leans on |
| `fig6_model_comparison.png` | ML vs baselines, predicted vs actual |
| `fig7_forecast.png` | 3-month forward forecast per ingredient |

## Deployment plan

- **API + model** run as one container image (the included `Dockerfile`). The
  same process serves the REST API, Swagger UI, and the forecasting endpoints. The model is light enough to retrain in-process, so there's no separate model
  server to operate. Target host: a managed container platform (Render, Railway,
  Fly.io) or a small VPS, fronted by the platform's TLS.
- **Database:** a managed PostgreSQL 16 instance. On first deploy run
  `alembic upgrade head`, then the two seeders. Connection details and
  `SECRET_KEY` come from environment variables injected at deploy time.
- **Model refresh:** prices update monthly, so a scheduled job
  (`POST /forecasts/refresh`, or a cron calling the same service) retrains and
  rewrites forecasts as new WFP data lands. Forecasts are upserted, so a refresh
  never orphans a forecast a past formulation already referenced.
- **CI (later phase):** GitHub Actions running `test_optimizer.py` plus the two e2e
  scripts against a Postgres service container, building the image on green.
- **Client (later phase):** the Flutter app consumes this same API, with a
  trimmed on-device NSGA-II and a SQLite cache for offline use.

## Status and limitations

The backend, optimiser, forecasting, and the ML <-> optimiser coupling are working
and verified end-to-end against PostgreSQL. However, current 29 months of history
is short, so annual seasonality is only weakly identifiable and the gradient
booster is competitive with a random walk on raw error. Its real edge is the directional signal it gives the optimiser, which a flat forecast can't.
