from data.generator import demo_scenario
from optimization.risk_loop import optimize
from simulation.disruptions import simulate_breakdown, reoptimize, monitor_conditions


def test_breakdown_redistributes_every_affected_delivery():
    s = demo_scenario()
    before = optimize(s)
    broken = before.routes[0].truck_id
    changed, event = simulate_breakdown(s, before, broken)
    assert next(t for t in s.trucks if t.truck_id == broken).availability  # input preserved
    assert not next(t for t in changed.trucks if t.truck_id == broken).availability
    assert event['requires_reoptimization'] and event['effective_unserved_risk'] == 1
    after = reoptimize(changed, before, .15)
    assert after.accepted, after.model_dump()
    assert all(r.truck_id != broken for r in after.routes)
    assigned = {oid for r in after.routes for oid in r.order_ids}
    assert assigned == {o.order_id for o in s.orders}
    assert set(event['affected_order_ids']) <= assigned


def test_monitor_tighter_budget_triggers_reoptimization():
    s = demo_scenario()
    p = optimize(s, .35)
    result = monitor_conditions(s, p, .05)
    assert result['requires_reoptimization']
    assert result['plan'].accepted
    assert result['plan'].metrics['max_delay_risk'] <= .05


def test_monitor_unchanged_does_not_resolve():
    s = demo_scenario()
    p = optimize(s)
    result = monitor_conditions(s, p, .15)
    assert not result['requires_reoptimization'] and result['plan'] is None
