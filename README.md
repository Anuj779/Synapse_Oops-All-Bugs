# Adaptive Fleet AI

> **React interface:** A Vercel-ready Next.js operations workspace is available in [web/](web/README.md). The verified Streamlit interface remains available for the original offline demo.

**Risk-Budgeted Joint Route & Load Optimization** · Synapse 1.0 · AI in Automation

Problem Statement #2: “Intelligent Route & Load Optimization for Logistics Fleets: Design an AI system that optimizes delivery routes and load distribution across a fleet of trucks, factoring in fuel efficiency, delivery windows, traffic, and vehicle capacity, reducing cost and emissions per trip.”

The dispatcher chooses an acceptable delivery-risk limit. Adaptive Fleet AI jointly assigns trucks, allocates whole orders within capacity, and sequences deliveries. It seeks an economical feasible fleet plan within that limit. When a breakdown invalidates the plan, the system replans all pending deliveries across the remaining fleet.

The differentiation is the **product formulation**: dispatcher-defined risk budget, joint truck/load/route decisions, risk as a planning constraint, independent deterministic validation, and event-driven fleet-wide reoptimization. Route optimization and traffic-aware routing themselves are established techniques; no claim of global novelty is made.

**All bundled data and reported results are simulated. This prediction model is trained on synthetic demonstration data and is not production-validated. This prototype is decision support, not a safety-certification system.**

## Quick start

Tested on Windows with Python 3.14.7. The pinned dependencies target Python 3.14; other versions have not been verified. Initial package installation requires internet access. After installation, the complete core demo runs offline, including first-use model training and the route schematic.

From this directory in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m streamlit run ui/dashboard.py --server.address 127.0.0.1
```

Open `http://127.0.0.1:8501`. Activation is unnecessary. `requirements.txt` pins direct dependencies; `requirements-lock.txt` records the complete tested environment.

Optional API in a second terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

API documentation: `http://127.0.0.1:8000/docs`. The dashboard calls the same Python service layer directly, so it does not depend on an API subprocess to function. Keep both services local; production authentication and deployment are outside scope.

## Demo walkthrough

1. Click **Load demo mode**: five trucks and twelve orders on the Pune–Mumbai corridor, totaling 10,000 kg. Expand Fleet setup to inspect/edit availability, capacity, starting locations, fuel efficiency and costs. Orders expose weights, windows, service times, priorities, coordinates and regions. Click **Apply setup** to validate edits and invalidate old results.
2. Click **Generate Baseline**. This uses sequential truck allocation and nearest feasible next deliveries, without a risk constraint. Inspect calculated KPIs and route assignments.
3. Select **Balanced**, default 15%, and click **Optimize Fleet**. Review PASS/REJECT, selected risk, truck loads, route order, ETAs and Why this plan.
4. Try **Economy** (35%) and **Reliable** (5%), or move the 1–50% slider. Click Optimize Fleet after each change. The risk loop table shows rejected candidates and tightening. Modes can legitimately produce the same plan if it already satisfies both budgets. Stricter risk does not guarantee higher reported cost because search is heuristic.
5. Select an assigned truck and click **Simulate Breakdown**. See unavailable vehicle, affected orders, remaining fleet capacity and invalidation reasons. With automatic reoptimization enabled, a replacement plan is generated immediately.
6. For the staged presentation, disable automatic reoptimization first. The invalid old plan remains visible as a historical comparison; click **Re-optimize** to recover. Before/event/after tables and explanations show actual changes and order reassignment.
7. Download plan JSON and scenario JSON. Load demo mode resets the session; it does not overwrite input CSVs.

The breakdown occurs **before departure**, while all freight is at the depot and all deliveries remain pending. The demo does not simulate roadside unloading, travel progress or completed stops. A broken assigned truck gives affected orders 100% non-service risk until reassignment; this is an event status, not an XGBoost prediction. After an event, the pre-event plan is historical, and only an accepted recovered plan is usable.

## Architecture and workflow

```text
CSV / editable scenario
    → routing matrix (cache → configured Valhalla → offline fallback)
    → XGBoost ETA + calibrated synthetic uncertainty
    → OR-Tools truck assignment + capacity + route sequence
    → independent feasibility and risk validation
    → accepted fleet plan / explicit failure
    → condition event → validation → bounded fleet-wide reoptimization
```

| Component | Implementation |
|---|---|
| Python, Pandas, Pydantic | Typed scenarios, deterministic generators and CSV loading |
| XGBoost, scikit-learn | Synthetic ETA training, calibration and held-out evaluation |
| Google OR-Tools | Joint vehicle routing with load, time and eligibility constraints |
| Valhalla / OpenStreetMap | Optional truck road-distance/travel-time matrix |
| Deterministic fallback | Great-circle distance × 1.25, nominal speed 55 km/h |
| FastAPI | Demo, baseline, optimize, breakdown, monitor and reoptimize endpoints |
| Streamlit / Plotly | Editable setup, risk controls, KPI comparison and offline schematic |
| SQLite | Local timestamped plan and simulation-event audit history |

Modules: `app/` configuration/API/services/storage; `models/` schemas; `data/` generation and samples; `risk/` training/prediction; `routing/` cache/provider/fallback; `optimization/` baseline/solver/risk-loop/validation; `metrics/` accounting; `simulation/` events; `ui/` dashboard; `tests/` automated validation; `scripts/smoke_demo.py` reproducible demo report.

## Risk and optimization logic

**Budget definition:** the maximum predicted probability of lateness among all orders must not exceed the chosen limit. A 15% budget is a per-delivery cap, not a 15% probability that the entire fleet will avoid all failures.

XGBoost predicts leg travel minutes from nominal route time, traffic severity, weather severity and disruption factor. Synthetic history contains 6,000 rows with seed 42. The split is 70% training, 15% uncertainty calibration and 15% final test. Calibration estimates relative prediction error; the test set is not used to fit that uncertainty. Demo delivery windows were selected to exercise the risk/cost tradeoff; they are not real customer commitments or independent business validation. A normal approximation and a common route-delay factor turn deadline slack into lateness probability:

```text
leg_sd = predicted_leg_minutes × calibrated_relative_sd
arrival_mean = previous_departure + predicted_leg_minutes, respecting opening times
arrival_sd = sum(leg_sd so far)
lateness_probability = 1 − NormalCDF((deadline − arrival_mean) / arrival_sd)
```

Adding leg SDs models fully correlated route delays. Waiting does not reduce the accumulated SD, making the calculation conservative around early opening times. These are transparent demonstration assumptions, not validated distributional guarantees.

OR-Tools creates one route per used truck, with whole orders assigned exactly once. It enforces vehicle capacity, availability, permitted regions, opening times, deadlines and a risk-adjusted time dimension. All routes start at minute zero (08:00) and return to the truck's starting location. Delivery deadlines constrain arrival/service start, not service completion. Service time delays subsequent deliveries.

The bounded loop first solves without an uncertainty buffer, independently checks actual risk, and then tightens buffered travel times toward `mean + NormalQuantile(1 − budget) × sd`. The default limit is three attempts of at most 650 ms search each. Every candidate is recomputed and validated; an invalid plan cannot receive PASS. A failed search returns **“No feasible plan found for selected risk budget.”** This is not proof of mathematical infeasibility.

Search objective in INR-equivalent units:

```text
distance × vehicle operating cost/km
+ full-load fuel proxy × fuel price
+ full-load fuel proxy × CO₂ factor × 2 INR/kg
+ leg uncertainty minutes × destination priority × 4 INR/minute
```

Fuel cost already accounts for fuel in the objective; it is not added a second time. The CO₂ and uncertainty weights are explicitly chosen demo preferences. Risk is also a hard acceptance constraint. Full-load fuel is a tractable arc-cost proxy; reported fuel is recalculated from actual remaining load. Consequently search score and reported monetary cost are not identical. The first accepted candidate is returned. The solver is a time-bounded heuristic and does not certify the cheapest possible plan; runtime and tie-breaking may vary slightly by machine.

`optimization/constraints.py` independently recomputes loads, arrivals and risks rather than trusting cached ETAs, submitted KPIs or solver status. It also rejects duplicate/missing orders, unknown IDs, unavailable trucks, duplicate truck routes and represented regional restrictions.

`POST /monitor` accepts an updated scenario, previous plan and current risk budget. It revalidates and automatically replans only when needed. The demo is event-driven; it does not poll live GPS or traffic feeds in the background.

## Metrics and explanations

For each loaded leg:

```text
fuel_L = distance_km / rated_kmpl × (0.8 + 0.2 × remaining_load / capacity)
fuel_cost_INR = fuel_L × FUEL_PRICE_INR
total_cost_INR = fuel_cost_INR + distance_km × operating_cost_per_km
CO₂_kg = fuel_L × CO2_KG_PER_LITRE
```

The empty return leg uses the 0.8 multiplier. These are demonstration coefficients, not measured vehicle calibration. Defaults: fuel price ₹95/L and emissions factor 2.68 kg/L. Neither is presented as current market pricing or a certified lifecycle emissions estimate.

Reported metrics include distance, fuel, fuel cost, operating-plus-fuel cost, CO₂, empty return kilometers, maximum delay risk, sum of delivery lateness probabilities (expected late deliveries), count of mean ETAs past deadline, load utilization over **used** trucks, orders served, truck count and solve/reoptimization time. Late deliveries are predictions, not measured outcomes. Costs exclude tolls, fixed dispatch fees and transfer costs.

Comparison percentages come only from computed outputs; negative improvements and cost increases remain visible. If coverage differs, the UI warns instead of claiming comparable savings. Explanations cite actual loads, capacity, risk, solve attempts and changed order-to-truck assignments; no LLM creates the reasoning.

## Data and local artifacts

- `data/sample_data/trucks.csv`, `orders.csv`, `road_conditions.csv`: readable, editable demo inputs. Missing files are generated independently; existing files are never silently overwritten. Malformed inputs produce validation errors.
- `data/sample_data/historical_delay.csv`: seeded synthetic training history, generated if absent. Existing historical data is preserved and validated before training.
- `artifacts/risk/eta.ubj`, `metadata.json`: saved model, split sizes, synthetic test MAE and interval coverage. Missing/unloadable model artifacts trigger a single local retraining attempt.
- `artifacts/routing/`: cached Valhalla matrices keyed by coordinates, endpoint and costing version. Invalid caches are rejected.
- `artifacts/fleet.sqlite3`: simple audit log. Plan/event payloads stored locally.
- `artifacts/demo_report.json`: actual outputs from the last smoke demo; do not treat these as measured real-world performance.

Train explicitly:

```powershell
.\.venv\Scripts\python.exe -m risk.model
```

Explicit training overwrites model artifacts but never overwrites historical CSV input. Restart running services after retraining because each process caches the loaded model.

## Optional routing and configuration

No paid API or key is needed. Offline mode is the default. The route chart is an offline coordinate schematic; it never implies straight lines are drivable roads.

To use a local Valhalla server with OpenStreetMap-derived tiles, set its base URL before starting the process:

```powershell
$env:VALHALLA_URL = 'http://127.0.0.1:8002'
```

The adapter calls `/sources_to_targets` with `costing=truck`. Cached matrices are preferred; a configured local or optional public endpoint gets one request with a two-second timeout, then the system falls back. No public endpoint is called by default. An outage or malformed matrix emits a warning and displays **Demo Fallback**. Live Valhalla infrastructure is optional and is not bundled; adapter behavior is tested with controlled responses, not a deployed road server.

`.env.example` documents optional process environment variables; `.env` is not automatically loaded. Set variables in your shell or deployment environment. Besides the routing URL, configurable values are fuel price, CO₂ factor, mode thresholds and `MAX_OPTIMIZATION_ITERATIONS` (bounded 1–6). UI thresholds use percentages; API budgets use probabilities between 0 and 0.5, excluding zero.

## Verification

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m scripts.smoke_demo
.\.venv\Scripts\python.exe -m pip check
```

Tests cover capacity, windows, risk-driven retries, valid plans, unavailable/restricted vehicles, missing and duplicate assignments, zero orders, deterministic CO₂ and hand-calculated fuel/cost, CSV preservation, model reproducibility, routing outage/cache handling, breakdown redistribution, automatic monitoring, API validation and complete Streamlit interaction flow.

The smoke report executes baseline → Economy/Balanced/Reliable → truck breakdown → automatic fleet-wide recovery. All original orders must be served before it reports PASS. The UI test uses Streamlit's AppTest to click the actual demo controls. Live server startup can be checked at `/health` (API) and `/_stcore/health` (Streamlit).

## Limitations and future scope

This is a small, single-user hackathon prototype, sized for 5 trucks and 10–15 orders. Input guards cap fleets at 10 vehicles and 30 orders. It does not include telematics, live traffic, en-route physical transfer constraints, driver hours, road closures, axle/volume/stacking physics, authentication or enterprise integrations. Fallback routes cannot verify real road access, one-way streets or bridge restrictions. Regional eligibility is the only explicit route restriction beyond the optional Valhalla truck matrix.

Future work: calibrate on real fleet data, evaluate probability reliability under changing traffic, incorporate actual road geometry and vehicle-specific road restrictions, track completed/in-transit work, and benchmark solution quality against longer solves. These are future extensions, not implemented claims.

## Repository delivery

Target repository: [Anuj779/Synapse_Oops-All-Bugs](https://github.com/Anuj779/Synapse_Oops-All-Bugs). This project has its own Git history, isolated from the surrounding parent repository. `.gitignore` excludes environments, secrets, caches, databases, logs and generated model/report artifacts. Delivery checks include inspecting the remote, running the full tests/demo in a fresh environment, preparing a scoped commit, pushing without force, and verifying the remote commit. The current interface is Streamlit; a Vercel-oriented UI redesign is a subsequent phase.
