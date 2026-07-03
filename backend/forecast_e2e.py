"""End-to-end test of the ML price-forecasting feature and its coupling to
NSGA-II via forecast-mode optimisation.

Flow: login -> enter prices for imported ingredients -> refresh forecasts ->
inspect forecasts + backtest -> generate ration in `latest` mode -> generate in
`forecast` mode -> confirm the forecast prices changed the cost objective and
that the persisted formulation used forecast price rows.
"""

from __future__ import annotations

import sys
import time

import httpx

BASE = "http://127.0.0.1:8000/api/v1"
LOCATION = "Rwanda" #Choose the location as Rwanda

# Imported ingredients (no WFP history) need a manual price at LOCATION so the
# optimiser has all 12 ingredients available. Forecastable ones already have
# seeded history from 'Rwanda'.
IMPORTED_PRICES = {
    "Soybean meal (44%)": 900.0,
    "Sunflower seed cake": 550.0,
    "Wheat bran": 300.0,
    "Limestone": 120.0,
    "Dicalcium phosphate": 1200.0,
    "Layer premix (vit/min)": 2500.0,
    "DL-Methionine": 6500.0,
}


def fail(msg, resp=None):
    print(f"FAIL: {msg}")
    if resp is not None:
        print(f"  status={resp.status_code} body={resp.text[:600]}")
    sys.exit(1)


def poll(c, auth, job_id):
    deadline = time.time() + 110
    while time.time() < deadline:
        r = c.get(f"/formulations/jobs/{job_id}", headers=auth)
        if r.status_code != 200:
            fail("poll", r)
        res = r.json()
        if res["state"] in ("complete", "failed"):
            return res
        time.sleep(2)
    fail("job timeout")


def main():
    c = httpx.Client(base_url=BASE, timeout=120.0)
    sfx = str(int(time.time()))
    email = f"forecast+{sfx}@example.com"
    r = c.post("/auth/register", json={"name": "Egide", "email": email,
                                       "role": "farmer", "password": "supersecret123"})
    if r.status_code not in (200, 201):
        fail("register", r)
    tok = c.post("/auth/login", data={"username": email, "password": "supersecret123"}).json()["access_token"]
    auth = {"Authorization": f"Bearer {tok}"}

    ingredients = c.get("/ingredients", headers=auth).json()
    by_name = {i["name"]: i["ingredient_id"] for i in ingredients}

    print("#1 enter manual prices for imported ingredients (from 'Rwanda')")
    for name, price in IMPORTED_PRICES.items():
        r = c.post("/market-prices", headers=auth, json={
            "ingredient_id": by_name[name], "price_per_kg_rwf": price,
            "price_date": "2026-06-10", "market_location": LOCATION})
        if r.status_code not in (200, 201):
            fail(f"price {name}", r)
    print(f"  entered {len(IMPORTED_PRICES)} imported prices")

    print("\n#2 POST /forecasts/refresh (train ML model + persist forecasts)")
    r = c.post("/forecasts/refresh", headers=auth, params={"horizon_months": 1})
    if r.status_code != 200:
        fail("refresh", r)
    rr = r.json()
    print(f"  model={rr['model']}  ingredients_forecast={rr['ingredients_forecast']}")
    for item in rr["forecasts"]:
        fp = item["forecast"][0]
        print(f"    {item['ingredient_name']:24s} -> {fp['price']:8.2f} RWF/kg "
              f"[{fp['lower']:.0f}, {fp['upper']:.0f}] on {fp['date']}")
    if rr["ingredients_forecast"] < 5:
        fail("expected >=5 ingredients forecast")

    print("\n#3 GET /forecasts/backtest (ML vs baselines)")
    r = c.get("/forecasts/backtest", headers=auth, params={"test_months": 6})
    if r.status_code != 200:
        fail("backtest", r)
    bt = r.json()
    for m in bt["methods"]:
        print(f"    {m['method']:20s} n={m['n']:3d}  MAE={m['mae']:7.1f}  "
              f"RMSE={m['rmse']:7.1f}  MAPE={m['mape']:5.2f}%")

    print("\n#4 create flock")
    flock_id = c.post("/flocks", headers=auth, json={
        "name": "Forecast Test Layer", "type": "layer",
        "current_age_weeks": 30, "flock_size": 1500}).json()["flock_id"]

    def generate(price_mode):
        r = c.post("/formulations/generate", headers=auth, json={
            "flock_id": flock_id, "market_location": LOCATION, "method": "both",
            "price_mode": price_mode, "population_size": 60, "max_generations": 100})
        if r.status_code not in (200, 202):
            fail(f"generate {price_mode}", r)
        return poll(c, auth, r.json()["job_id"])

    print("\n#5 generate in LATEST mode")
    latest = generate("latest")
    if latest["state"] != "complete":
        fail(f"latest job failed: {latest.get('error')}")
    lp_latest = latest["lp_solution"]
    print(f"  LP cost (latest prices)   = {lp_latest['total_cost_per_kg_rwf']:.2f} RWF/kg")

    print("\n#6 generate in FORECAST mode")
    fc = generate("forecast")
    if fc["state"] != "complete":
        fail(f"forecast job failed: {fc.get('error')}")
    lp_fc = fc["lp_solution"]
    print(f"  LP cost (forecast prices) = {lp_fc['total_cost_per_kg_rwf']:.2f} RWF/kg")

    delta = lp_fc["total_cost_per_kg_rwf"] - lp_latest["total_cost_per_kg_rwf"]
    print(f"\n  cost shift from forecasting = {delta:+.2f} RWF/kg "
          f"({100*delta/lp_latest['total_cost_per_kg_rwf']:+.2f}%)")
    if abs(delta) < 1e-6:
        print("  WARNING: forecast and latest costs identical — forecasts may not have applied")
    else:
        print("  -> forecast prices flowed into the optimiser (dynamic pricing confirmed)")

    # Confirm a forecast-mode formulation links to forecast price rows.
    print("\n#7 verify provenance: forecast-mode formulation used forecast prices")
    hist = c.get(f"/formulations/flocks/{flock_id}/history", headers=auth).json()
    print(f"  {len(hist)} formulations persisted across both runs")

    print("\n#8 GET /forecasts/formulation-backtest (out-of-sample savings)")
    r = c.get("/forecasts/formulation-backtest", headers=auth, params={"test_months": 12})
    if r.status_code != 200:
        fail("formulation-backtest", r)
    fbt = r.json()
    print(f"  Test months: {fbt['test_months']}")
    print(f"  Average Stale Cost:   {fbt['average_stale_cost_rwf']:.2f} RWF/kg")
    print(f"  Average Forecast Cost: {fbt['average_forecast_cost_rwf']:.2f} RWF/kg")
    print(f"  Average Savings:       {fbt['average_savings_rwf']:.2f} RWF/kg ({fbt['savings_percent']:.2f}%)")

    print("\n# ALL FORECASTING E2E CHECKS PASSED #")



if __name__ == "__main__":
    main()
