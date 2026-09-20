"""Independent deterministic validation; never trust submitted stop ETAs or KPIs."""
from collections import Counter
from metrics.calculations import evaluate


def validate_plan(s, plan, matrix, mean, sigma, enforce_risk=True):
    reasons = []
    trucks = {t.truck_id: t for t in s.trucks}
    orders = {o.order_id: o for o in s.orders}
    seen = Counter(oid for r in plan.routes for oid in r.order_ids)
    if set(seen) != set(orders) or any(count != 1 for count in seen.values()):
        reasons.append('Rejected: every order must be assigned exactly once.')
    used = [r.truck_id for r in plan.routes]
    if len(used) != len(set(used)):
        reasons.append('Rejected: duplicate routes for a truck.')
    for route in plan.routes:
        truck = trucks.get(route.truck_id)
        if truck is None:
            reasons.append('Rejected: unknown truck.')
            continue
        if not truck.availability and route.order_ids:
            reasons.append(f'Rejected: vehicle {truck.truck_id} unavailable.')
        assigned = [orders[oid] for oid in route.order_ids if oid in orders]
        if sum(o.weight_kg for o in assigned) > truck.capacity_kg:
            reasons.append(f'Rejected: vehicle capacity insufficient ({truck.truck_id}).')
        if any(o.region in truck.forbidden_regions for o in assigned):
            reasons.append(f'Rejected: route restriction ({truck.truck_id}).')
    if any(r.truck_id not in trucks for r in plan.routes) or any(oid not in orders for oid in seen):
        return list(dict.fromkeys(reasons))
    checked = evaluate(s, plan.routes, matrix, mean, sigma, plan.kind, plan.risk_budget)
    for route in checked.routes:
        for stop in route.stops:
            if stop.eta_minutes > orders[stop.order_id].delivery_deadline + 1e-6:
                reasons.append(f'Rejected: delivery window infeasible ({stop.order_id}).')
            if enforce_risk and stop.delay_risk > plan.risk_budget + 1e-8:
                reasons.append(f'Rejected: predicted delay risk exceeds selected budget ({stop.order_id}).')
    return list(dict.fromkeys(reasons))
