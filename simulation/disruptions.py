"""Event-driven replan at dispatch time. All deliveries are still pending."""
from models.schemas import Plan, Scenario
from optimization.constraints import validate_plan
from optimization.risk_loop import optimize
from risk.model import predict_matrix
from routing.matrix import get_matrix


def simulate_breakdown(s: Scenario, plan: Plan, truck_id: str):
    if not plan.accepted:
        raise ValueError('An accepted plan is required before simulating a breakdown.')
    truck = next((t for t in s.trucks if t.truck_id == truck_id), None)
    if truck is None or not truck.availability:
        raise ValueError('Select an available truck.')
    changed = s.model_copy(deep=True)
    next(t for t in changed.trucks if t.truck_id == truck_id).availability = False
    affected = [oid for r in plan.routes if r.truck_id == truck_id for oid in r.order_ids]
    matrix = get_matrix(changed)
    mean, sigma = predict_matrix(matrix, changed.conditions)
    reasons = validate_plan(changed, plan, matrix, mean, sigma)
    event = dict(type='TRUCK_BREAKDOWN', truck_id=truck_id, affected_order_ids=affected,
                 pending_order_ids=[o.order_id for o in changed.orders],
                 remaining_capacity_kg=sum(t.capacity_kg for t in changed.trucks if t.availability),
                 remaining_trucks=[t.truck_id for t in changed.trucks if t.availability],
                 old_plan_valid=not reasons, validation_reasons=reasons,
                 requires_reoptimization=bool(reasons),
                 stranded_orders=len(affected),
                 effective_unserved_risk=1.0 if affected else plan.metrics.get('max_delay_risk', 0),
                 timing='Pre-dispatch: all deliveries pending; freight can be reassigned at the depot.')
    return changed, event


def reoptimize(s: Scenario, previous: Plan, budget: float):
    result = optimize(s, budget)
    result.kind = 'reoptimized'
    if result.accepted:
        old_assignment = {oid: r.truck_id for r in previous.routes for oid in r.order_ids}
        moves = [(oid, old_assignment.get(oid), r.truck_id) for r in result.routes for oid in r.order_ids
                 if old_assignment.get(oid) != r.truck_id]
        result.explanations.insert(0, f"Cost changed by ₹{result.metrics['cost_inr']-previous.metrics.get('cost_inr', 0):+,.0f} versus the pre-event plan, with {len(moves)} deliveries assigned to a different truck.")
        result.explanations.extend(f'{oid} moved from {old} to {new}.' for oid, old, new in moves)
    return result


def monitor_conditions(s: Scenario, previous: Plan, budget: float, auto_reoptimize=True):
    matrix = get_matrix(s)
    mean, sigma = predict_matrix(matrix, s.conditions)
    checked = previous.model_copy(deep=True)
    checked.risk_budget = budget
    reasons = validate_plan(s, checked, matrix, mean, sigma)
    return {'requires_reoptimization': bool(reasons), 'reasons': reasons,
            'plan': reoptimize(s, previous, budget) if reasons and auto_reoptimize else None}
