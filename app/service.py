from optimization.baseline import baseline
from optimization.constraints import validate_plan
from optimization.risk_loop import optimize
from risk.model import predict_matrix
from routing.matrix import get_matrix
from simulation.disruptions import simulate_breakdown, reoptimize, monitor_conditions
from app.storage import record


def generate_baseline(s, budget=.15):
    matrix = get_matrix(s)
    mean, sigma = predict_matrix(matrix, s.conditions)
    result = baseline(s, matrix, mean, sigma, budget)
    errors = validate_plan(s, result, matrix, mean, sigma, enforce_risk=False)
    result.accepted = not errors
    result.reasons += errors
    record('baseline', result.model_dump())
    return result


def optimize_fleet(s, budget=.15):
    result = optimize(s, budget)
    record('optimized', result.model_dump())
    return result


def breakdown(s, plan, truck_id, auto=True):
    changed, event = simulate_breakdown(s, plan, truck_id)
    record('event', event)
    result = reoptimize_fleet(changed, plan, plan.risk_budget) if auto and event['requires_reoptimization'] else None
    return changed, event, result


def reoptimize_fleet(s, previous, budget):
    result = reoptimize(s, previous, budget)
    record('reoptimized', result.model_dump())
    return result
