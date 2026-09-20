import time
import numpy as np
from metrics.calculations import evaluate
from models.schemas import Route, Scenario
from routing.matrix import get_matrix


def baseline(s: Scenario, matrix=None, mean=None, sigma=None, budget=.15):
    """Truck-order nearest feasible greedy, without any risk constraint."""
    started = time.perf_counter()
    matrix = matrix if matrix is not None else get_matrix(s)
    mean = mean if mean is not None else matrix.minutes*(1+.5*s.conditions.traffic_severity)
    sigma = sigma if sigma is not None else mean*.12
    unassigned = set(range(len(s.orders)))
    assignments = []
    for vehicle, truck in enumerate(s.trucks):
        if not truck.availability:
            continue
        load, clock, previous, ids = 0, 0., vehicle, []
        for _ in range(len(s.orders)):
            feasible = [i for i in sorted(unassigned) if
                        load+s.orders[i].weight_kg <= truck.capacity_kg and
                        s.orders[i].region not in truck.forbidden_regions and
                        max(s.orders[i].window_start, clock+mean[previous, len(s.trucks)+i]) <= s.orders[i].delivery_deadline]
            if not feasible:
                break
            i = min(feasible, key=lambda i: (matrix.distance[previous, len(s.trucks)+i], i))
            order, node = s.orders[i], len(s.trucks)+i
            clock = max(order.window_start, clock+mean[previous, node]) + order.service_time
            previous, load = node, load+order.weight_kg
            ids.append(order.order_id)
            unassigned.remove(i)
        if ids:
            assignments.append(Route(truck_id=truck.truck_id, order_ids=ids))
    plan = evaluate(s, assignments, matrix, mean, sigma, budget=budget)
    plan.accepted = not unassigned
    plan.reasons = ['Baseline ignores the risk budget.']
    if unassigned:
        plan.reasons.append('Unserved orders: ' + ', '.join(s.orders[i].order_id for i in sorted(unassigned)))
    plan.elapsed_seconds = time.perf_counter()-started
    return plan
