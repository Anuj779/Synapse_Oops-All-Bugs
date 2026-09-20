"""Run from the project root: python -m scripts.smoke_demo."""
import json
from pathlib import Path
from app.config import ARTIFACT_DIR
from app.service import generate_baseline, optimize_fleet, breakdown
from data.generator import load_scenario


def main():
    scenario = load_scenario()
    baseline = generate_baseline(scenario)
    plans = {mode: optimize_fleet(scenario, budget) for mode, budget in [('Economy', .35), ('Balanced', .15), ('Reliable', .05)]}
    assert baseline.accepted, baseline.reasons
    for name, plan in plans.items():
        assert plan.accepted, (name, plan.reasons)
        assert plan.metrics['max_delay_risk'] <= plan.risk_budget
    before = plans['Balanced']
    changed, event, after = breakdown(scenario, before, before.routes[0].truck_id)
    assert after and after.accepted, after.reasons if after else 'Recovery not triggered'
    assert after.metrics['orders_served'] == len(scenario.orders)
    report = {'simulated': True, 'baseline': baseline.model_dump(),
              'risk_modes': {name: p.model_dump() for name, p in plans.items()},
              'event': event, 'reoptimized': after.model_dump()}
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    path = ARTIFACT_DIR / 'demo_report.json'
    path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('PASS: baseline -> risk modes -> breakdown -> fleet-wide recovery')
    for name, p in [('Baseline', baseline), *plans.items(), ('Recovered', after)]:
        print(f"{name:10} cost INR {p.metrics['cost_inr']:9.2f} | max risk {p.metrics['max_delay_risk']:.2%} | trucks {p.metrics['trucks_used']} | solve {p.elapsed_seconds:.2f}s")
    print(f'Report: {path}')


if __name__ == '__main__':
    main()
