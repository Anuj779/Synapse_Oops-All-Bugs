Current Phase: 16 - React UI rebuild complete and ready to push
Current Feature: complete offline Streamlit/FastAPI prototype with automatic recovery
Last Verified Test: fresh locked environment and clean source copy: 22 tests passed (21.36s); full demo passed; Streamlit startup health passed; pip check passed.
Known Issue: third-party deprecation warnings; optional live Valhalla not deployed/tested (adapter/cache/outage behavior tested)
Next Action: commit and push the Vercel-ready React interface; then deploy the Python API and connect Vercel with BACKEND_API_URL.
Architecture Decisions: Python/FastAPI/Streamlit; OR-Tools routing; XGBoost ETA with explicit uncertainty; SQLite plan/event history; offline matrix fallback
Do-Not-Change Constraints: risk must constrain decisions; simulated data labeled; bounded loops; no paid dependency; no push before GitHub URL; preserve parent repository work

Checkpoints:
- Phase 1: validated data loading, IDs/windows, non-overwrite behavior.
- Phase 2: nearest feasible baseline and deterministic metrics passed.
- Phase 3: seeded synthetic XGBoost training, calibration/test separation, local persistence and predictions passed.
- Phase 4: bounded quantile loop passed; Economy and Reliable produce different accepted routes.
- Phase 5: independently recomputed capacity/window/risk checks reject violations.
- Phase 6: 12 orders served within Balanced risk; impossible fleet reports failure.
- Phase 7: breakdown marks selected vehicle unavailable and identifies stranded orders.
- Phase 8: recovery redistributes all orders; condition monitor triggers only when validation fails.
- Phase 9: Streamlit interactive smoke and FastAPI endpoints passed.
- Phase 10: explanations derived from loads, budgets, costs, iterations and actual assignment changes.
- Phase 11: full suite 21 passed; offline CLI smoke report generated.
- Phase 12: browser-rendered layout inspected; reset-only float default issue fixed and regression-tested.
- Phase 13: README, pinned direct dependencies, complete lockfile, environment example and ignore rules prepared. No GitHub URL received; no commit/push.
- Phase 14: 22 final tests passed, including manual recovery, changed-budget invalidation and demo reset. Full browser recovery and CLI smoke passed. Ignore rules checked; no credential-pattern matches in deliverable source. Parent work untouched.

Local services: Streamlit http://127.0.0.1:8501 ; FastAPI http://127.0.0.1:8000/docs
Latest simulated smoke: baseline INR 16809.05 / risk 35.50%; Balanced INR 15407.50 / risk 8.56%; Reliable INR 18341.64 / risk 4.29%; recovered INR 15986.17 / risk 8.56%. Bounded heuristic output may vary slightly by run.
GitHub delivery: target inspected and empty; isolated project Git history; 47 source/data/documentation files reviewed; no environments, logs, credentials or generated model artifacts staged.

React checkpoint: Next.js 16 and Fluent UI operations workspace; build and lint pass; 0 npm vulnerabilities; desktop and 390x844 mobile layouts inspected; live breakdown recovery verified against FastAPI.
