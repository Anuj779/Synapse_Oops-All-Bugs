from statistics import NormalDist
import time
from app.config import MAX_OPTIMIZATION_ITERATIONS
from metrics.calculations import evaluate
from models.schemas import Plan
from optimization.constraints import validate_plan
from optimization.solver import solve_candidate
from risk.model import predict_matrix
from routing.matrix import get_matrix


def optimize(s, budget=.15, matrix=None, mean=None, sigma=None):
    if not 0 < budget <= .5:
        raise ValueError('Risk budget must be greater than 0 and at most 50%.')
    started = time.perf_counter()
    matrix = matrix if matrix is not None else get_matrix(s)
    if mean is None or sigma is None:
        mean, sigma = predict_matrix(matrix, s.conditions)
    z = NormalDist().inv_cdf(1-budget)
    history = []
    # Start unbuffered, tighten conservatively. Last iteration enforces full selected quantile.
    levels = [z] if MAX_OPTIMIZATION_ITERATIONS == 1 else [z*i/(MAX_OPTIMIZATION_ITERATIONS-1) for i in range(MAX_OPTIMIZATION_ITERATIONS)]
    for i, safety_z in enumerate(levels):
        assignments = solve_candidate(s, matrix, mean, sigma, safety_z)
        if assignments is None:
            history.append(dict(iteration=i+1, safety_z=safety_z, status='NO_CANDIDATE'))
            # A heuristic search failure is not a mathematical proof of infeasibility.
            continue
        plan = evaluate(s, assignments, matrix, mean, sigma, 'optimized', budget)
        reasons = validate_plan(s, plan, matrix, mean, sigma)
        history.append(dict(iteration=i+1, safety_z=safety_z, max_risk=plan.metrics['max_delay_risk'],
                            cost_inr=plan.metrics['cost_inr'], status='PASS' if not reasons else 'REJECT', reasons=reasons))
        if reasons:
            continue
        plan.accepted, plan.iterations = True, history
        plan.elapsed_seconds = time.perf_counter()-started
        plan.explanations = [f"Maximum delivery lateness risk {plan.metrics['max_delay_risk']:.1%} is within the selected {budget:.1%} budget.",
                             'Every order is assigned once; capacity, availability, regional restrictions and predicted delivery windows pass independent validation.',
                             f'Accepted after {len(history)} bounded solve attempt(s); search balances operating cost, fuel, CO₂ and travel uncertainty.']
        for route in plan.routes:
            truck = next(t for t in s.trucks if t.truck_id == route.truck_id)
            plan.explanations.append(f'{truck.truck_id} carries {route.load_kg:,} / {truck.capacity_kg:,} kg across {len(route.order_ids)} deliveries; estimated cost ₹{route.cost_inr:,.0f}.')
        return plan
    return Plan(kind='optimized', risk_budget=budget, reasons=[
        'No feasible plan found for selected risk budget.',
        'Bounded heuristic search could not satisfy all orders, capacities, availability, delivery windows, regional restrictions and risk. Try a higher budget, wider windows or additional capacity.'],
        iterations=history, routing_mode=matrix.mode, elapsed_seconds=time.perf_counter()-started)
