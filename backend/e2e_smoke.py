"""End-to-end smoke test: exercises the full user journey against the live
ASGI server backed by real PostgreSQL.

Flow: register -> login -> me -> list ingredients -> create flock ->
enter 12 market prices -> generate (both engines) -> poll job ->
inspect Pareto front -> history -> select a formulation -> export PDF + CSV.

Run while uvicorn is serving on 127.0.0.1:8000.
"""

from __future__ import annotations

import sys
import time

import httpx

BASE = "http://127.0.0.1:8000/api/v1"
LOCATION = "Kigali"

# Realistic Kigali prices (RWF/kg) keyed by ingredient name.
PRICES = {
    "Whole maize grain": 450.0,
    "Soybean meal (44%)": 900.0,
    "Sunflower seed cake": 550.0,
    "Fishmeal (65% CP)": 1800.0,
    "Wheat bran": 300.0,
    "Cassava meal": 400.0,
    "Limestone": 120.0,
    "Dicalcium phosphate": 1200.0,
    "Sodium chloride (salt)": 350.0,
    "Layer premix (vit/min)": 2500.0,
    "Crude palm oil": 1600.0,
    "DL-Methionine": 6500.0,
}


def section(msg: str) -> None:
    print(f"\n## {msg} ##")


def fail(msg: str, resp: httpx.Response | None = None) -> None:
    print(f"FAIL: {msg}")
    if resp is not None:
        print(f"  status={resp.status_code} body={resp.text[:500]}")
    sys.exit(1)


def main() -> None:
    c = httpx.Client(base_url=BASE, timeout=120.0)
    suffix = str(int(time.time()))
    email = f"egide+{suffix}@example.com"
    password = "supersecret123"

    # 1. Register
    section("register farmer")
    r = c.post("/auth/register", json={
        "name": "Egide Harerimana",
        "email": email,
        "role": "farmer",
        "password": password,
    })
    if r.status_code not in (200, 201):
        fail("register", r)
    user = r.json()
    print(f"  user_id={user['user_id']} email={user['email']} role={user['role']}")

    # 2. Login (OAuth2 password form: username=email)
    section("login")
    r = c.post("/auth/login", data={"username": email, "password": password})
    if r.status_code != 200:
        fail("login", r)
    token = r.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    print(f"  token acquired ({len(token)} chars)")

    # 3. /me
    section("auth/me")
    r = c.get("/auth/me", headers=auth)
    if r.status_code != 200 or r.json()["email"] != email:
        fail("auth/me", r)
    print(f"  confirmed identity: {r.json()['name']}")

    # 4. Ingredients
    section("list ingredients")
    r = c.get("/ingredients", headers=auth)
    if r.status_code != 200:
        fail("list ingredients", r)
    ingredients = r.json()
    by_name = {i["name"]: i["ingredient_id"] for i in ingredients}
    print(f"  {len(ingredients)} ingredients in library")
    if len(ingredients) != 12:
        fail(f"expected 12 ingredients, got {len(ingredients)}")

    # 5. Create flock (layer)
    section("create flock")
    r = c.post("/flocks", headers=auth, json={
        "name": "Nyagatare Layer House A",
        "type": "layer",
        "current_age_weeks": 30,
        "flock_size": 2000,
    })
    if r.status_code not in (200, 201):
        fail("create flock", r)
    flock = r.json()
    flock_id = flock["flock_id"]
    print(f"  flock_id={flock_id} type={flock['type']} prev_form={flock['previous_formulation_id']}")

    # 6. Enter market prices for all 12 ingredients
    section("enter market prices")
    for name, price in PRICES.items():
        iid = by_name.get(name)
        if iid is None:
            fail(f"ingredient not found in library: {name}")
        r = c.post("/market-prices", headers=auth, json={
            "ingredient_id": iid,
            "price_per_kg_rwf": price,
            "price_date": "2026-06-11",
            "market_location": LOCATION,
        })
        if r.status_code not in (200, 201):
            fail(f"price for {name}", r)
    print(f"  entered {len(PRICES)} prices at {LOCATION}")

    r = c.get("/market-prices/latest", headers=auth, params={"market_location": LOCATION})
    if r.status_code != 200 or len(r.json()) != 12:
        fail("latest prices", r)
    print(f"  /latest returns {len(r.json())} current prices")

    # 7. Generate (both engines) — modest params for a fast wiring test
    section("generate formulation (both engines)")
    r = c.post("/formulations/generate", headers=auth, json={
        "flock_id": flock_id,
        "market_location": LOCATION,
        "method": "both",
        "population_size": 80,
        "max_generations": 150,
    })
    if r.status_code not in (200, 202):
        fail("generate", r)
    job = r.json()
    job_id = job["job_id"]
    print(f"  job_id={job_id} state={job['state']}")

    # 8. Poll job
    section("poll job")
    deadline = time.time() + 110
    result = None
    while time.time() < deadline:
        r = c.get(f"/formulations/jobs/{job_id}", headers=auth)
        if r.status_code != 200:
            fail("poll", r)
        result = r.json()
        if result["state"] in ("complete", "failed"):
            break
        time.sleep(2)
    if result is None or result["state"] != "complete":
        fail(f"job did not complete: {result}")
    front = result["nsga2_front"]
    lp = result["lp_solution"]
    print(f"  state=complete  nsga2_front={len(front)} points  lp_solution={'yes' if lp else 'no'}")
    if lp:
        print(f"  LP: cost={lp['total_cost_per_kg_rwf']:.2f} RWF/kg  dtsi={lp['dtsi_score']:.4f}")
    if front:
        costs = [p["total_cost_per_kg_rwf"] for p in front]
        dtsis = [p["dtsi_score"] for p in front]
        print(f"  NSGA-II cost range: {min(costs):.2f} - {max(costs):.2f} RWF/kg")
        print(f"  NSGA-II dtsi range: {min(dtsis):.4f} - {max(dtsis):.4f}")
        cheapest = min(front, key=lambda p: p["total_cost_per_kg_rwf"])
        print("  cheapest NSGA-II ration:")
        for nm, pct in sorted(cheapest["proportions"].items(), key=lambda kv: -kv[1]):
            if pct >= 0.05:
                print(f"     {nm:28s} {pct:6.2f}%")
    if not front and not lp:
        fail("no solutions produced")

    # 9. History
    section("flock history")
    r = c.get(f"/formulations/flocks/{flock_id}/history", headers=auth)
    if r.status_code != 200:
        fail("history", r)
    history = r.json()
    print(f"  {len(history)} formulations persisted for this flock")
    if not history:
        fail("history empty")

    # pick the cheapest persisted formulation to select
    target = min(history, key=lambda f: f["total_cost_per_kg_rwf"])
    target_id = target["formulation_id"]

    # 10. Detail
    section("formulation detail")
    r = c.get(f"/formulations/{target_id}", headers=auth)
    if r.status_code != 200:
        fail("detail", r)
    detail = r.json()
    print(f"  formulation {target_id}: {detail['generated_by']} "
          f"cost={detail['total_cost_per_kg_rwf']:.2f} dtsi={detail['dtsi_score']:.4f} "
          f"cosine={detail.get('cosine_distance')}")
    print(f"  {len(detail['ingredients'])} ingredient lines, names resolved: "
          f"{all(i.get('ingredient_name') for i in detail['ingredients'])}")

    # 11. Select
    section("select formulation")
    r = c.post(f"/formulations/{target_id}/select", headers=auth)
    if r.status_code not in (200, 204):
        fail("select", r)
    # verify flock now points at it and it is marked selected
    r = c.get(f"/flocks/{flock_id}", headers=auth)
    prev = r.json()["previous_formulation_id"]
    r = c.get(f"/formulations/{target_id}", headers=auth)
    is_sel = r.json()["is_selected"]
    print(f"  flock.previous_formulation_id={prev}  formulation.is_selected={is_sel}")
    if prev != target_id or not is_sel:
        fail("selection did not propagate")

    # 12. Export PDF + CSV
    section("export")
    r = c.get(f"/formulations/{target_id}/export", headers=auth, params={"format": "csv"})
    if r.status_code != 200 or "ingredient" not in r.text.lower():
        fail("csv export", r)
    csv_bytes = len(r.content)
    with open("/tmp/formulation_export.csv", "wb") as fh:
        fh.write(r.content)
    print(f"  CSV: {csv_bytes} bytes -> /tmp/formulation_export.csv")

    r = c.get(f"/formulations/{target_id}/export", headers=auth, params={"format": "pdf"})
    if r.status_code != 200 or not r.content.startswith(b"%PDF"):
        fail("pdf export", r)
    with open("/tmp/formulation_export.pdf", "wb") as fh:
        fh.write(r.content)
    print(f"  PDF: {len(r.content)} bytes -> /tmp/formulation_export.pdf (valid %PDF header)")

    section("ALL END-TO-END CHECKS PASSED")


if __name__ == "__main__":
    main()
