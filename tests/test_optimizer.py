import pytest
from data.generator import demo_scenario
from risk.model import predict_matrix
from routing.matrix import fallback
from optimization.risk_loop import optimize
from optimization.constraints import validate_plan
from models.schemas import Plan, Route


@pytest.fixture(scope='module')
def solved():
    s = demo_scenario()
    m = fallback(s)
    mean, sd = predict_matrix(m, s.conditions)
    return s, m, mean, sd, optimize(s, .15, m, mean, sd)


def test_valid_plan(solved):
    s, m, mean, sd, p = solved
    assert p.accepted, p.model_dump()
    assert not validate_plan(s, p, m, mean, sd)
    assert p.metrics['orders_served'] == 12
    assert p.metrics['max_delay_risk'] <= .15


def test_capacity_and_missing_rejected(solved):
    s, m, mean, sd, _ = solved
    p = Plan(kind='test', risk_budget=.15, routes=[Route(truck_id='T1', order_ids=[o.order_id for o in s.orders])])
    assert any('capacity' in r for r in validate_plan(s, p, m, mean, sd))
    p.routes[0].order_ids.pop()
    assert any('exactly once' in r for r in validate_plan(s, p, m, mean, sd))


def test_window_and_risk_rejected(solved):
    s, m, mean, sd, p = solved
    changed = s.model_copy(deep=True)
    changed.orders[-1].delivery_deadline = 1
    assert any('window' in r for r in validate_plan(changed, p, m, mean, sd))
    strict = p.model_copy(deep=True)
    strict.risk_budget = 0
    assert any('risk' in r for r in validate_plan(s, strict, m, mean, sd))


def test_risk_budget_changes_plan(solved):
    s, m, mean, sd, _ = solved
    economy = optimize(s, .35, m, mean, sd)
    reliable = optimize(s, .05, m, mean, sd)
    assert economy.accepted and reliable.accepted
    assert reliable.metrics['max_delay_risk'] <= .05
    assert reliable.metrics['max_delay_risk'] < economy.metrics['max_delay_risk']
    assert [r.order_ids for r in reliable.routes] != [r.order_ids for r in economy.routes]
    assert any(it['status'] == 'REJECT' for it in reliable.iterations)


def test_impossible_returns_honest_failure(solved):
    s, m, mean, sd, _ = solved
    s = s.model_copy(deep=True)
    for t in s.trucks:
        t.availability = False
    p = optimize(s, .15, m, mean, sd)
    assert not p.accepted and not p.routes
    assert len(p.iterations) <= 3


def test_restrictions_and_unknown_ids_rejected(solved):
    s, m, mean, sd, p = solved
    s = s.model_copy(deep=True)
    for t in s.trucks:
        t.forbidden_regions = ['corridor']
    assert any('restriction' in reason for reason in validate_plan(s, p, m, mean, sd))
    assert not optimize(s, .15, m, mean, sd).accepted
    invalid = p.model_copy(deep=True)
    invalid.routes[0].order_ids.append('UNKNOWN')
    assert any('exactly once' in reason for reason in validate_plan(s, invalid, m, mean, sd))


def test_empty_orders():
    s = demo_scenario()
    s.orders = []
    p = optimize(s)
    assert p.accepted and p.metrics['orders_served'] == 0
