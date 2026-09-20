import pytest
from data.generator import demo_scenario
from optimization.baseline import baseline
from app.config import CO2_FACTOR, FUEL_PRICE


def test_baseline_metrics():
    s = demo_scenario()
    p = baseline(s)
    assert p.accepted
    assert p.metrics['orders_served'] == 12
    assert p.metrics['co2_kg'] == pytest.approx(p.metrics['fuel_litres']*CO2_FACTOR)
    assert p.metrics['fuel_cost_inr'] == pytest.approx(p.metrics['fuel_litres']*FUEL_PRICE)
    assert p.metrics['distance_km'] == pytest.approx(sum(r.distance_km for r in p.routes))
    assert p.metrics['empty_km'] > 0
    for r in p.routes:
        t = next(t for t in s.trucks if t.truck_id == r.truck_id)
        assert r.load_kg <= t.capacity_kg
