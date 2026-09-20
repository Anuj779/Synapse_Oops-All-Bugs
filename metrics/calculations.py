from statistics import NormalDist
import numpy as np
from app.config import CO2_FACTOR, FUEL_PRICE
from models.schemas import Plan, Route, Scenario, Stop
from routing.matrix import Matrix


def lateness_risk(mean: float, sigma: float, deadline: float) -> float:
    return 1 - NormalDist().cdf((deadline-mean)/sigma) if sigma > 0 else float(mean > deadline)


def evaluate(s: Scenario, assignments: list[Route], matrix: Matrix, mean: np.ndarray,
             sigma: np.ndarray, kind='baseline', budget=.15) -> Plan:
    """Conservative common-delay factor: route SD is the sum of arc SDs.

    Waiting increases the mean without reducing SD (deliberately conservative).
    All routes return to their own starting depot. No pickup or split deliveries.
    """
    trucks = {t.truck_id: (i, t) for i, t in enumerate(s.trucks)}
    orders = {o.order_id: (len(s.trucks)+i, o) for i, o in enumerate(s.orders)}
    routes = []
    for assignment in assignments:
        start, truck = trucks[assignment.truck_id]
        route = Route(truck_id=truck.truck_id, order_ids=list(assignment.order_ids))
        route.load_kg = sum(orders[oid][1].weight_kg for oid in route.order_ids)
        remaining, previous, clock, spread = route.load_kg, start, 0., 0.
        for oid in route.order_ids:
            node, order = orders[oid]
            km = matrix.distance[previous, node]
            route.distance_km += km
            route.fuel_litres += km / truck.fuel_efficiency_kmpl * (.8 + .2 * remaining/truck.capacity_kg)
            clock = max(order.window_start, clock + mean[previous, node])
            spread += sigma[previous, node]
            route.stops.append(Stop(order_id=oid, eta_minutes=clock,
                                    delay_risk=lateness_risk(clock, spread, order.delivery_deadline)))
            clock += order.service_time
            remaining -= order.weight_kg
            previous = node
        if route.order_ids:
            route.empty_km = float(matrix.distance[previous, start])
            route.distance_km += route.empty_km
            route.fuel_litres += route.empty_km/truck.fuel_efficiency_kmpl*.8
        route.co2_kg = route.fuel_litres * CO2_FACTOR
        route.cost_inr = route.distance_km*truck.operating_cost_per_km + route.fuel_litres*FUEL_PRICE
        routes.append(route)
    stops = [stop for r in routes for stop in r.stops]
    capacity = sum(trucks[r.truck_id][1].capacity_kg for r in routes if r.order_ids)
    metrics = {key: sum(getattr(r, field) for r in routes) for key, field in
               [('distance_km', 'distance_km'), ('fuel_litres', 'fuel_litres'), ('cost_inr', 'cost_inr'),
                ('co2_kg', 'co2_kg'), ('empty_km', 'empty_km')]}
    metrics.update(fuel_cost_inr=metrics['fuel_litres']*FUEL_PRICE,
                   max_delay_risk=max((stop.delay_risk for stop in stops), default=0),
                   expected_late_deliveries=sum(stop.delay_risk for stop in stops),
                   late_deliveries=sum(stop.eta_minutes > orders[stop.order_id][1].delivery_deadline for stop in stops),
                   load_utilization=sum(r.load_kg for r in routes)/capacity if capacity else 0,
                   trucks_used=sum(bool(r.order_ids) for r in routes), orders_served=len(stops))
    return Plan(kind=kind, routes=routes, risk_budget=budget, metrics=metrics, routing_mode=matrix.mode)
