"""Joint assignment, capacity and sequence via OR-Tools RoutingModel."""
import math
from ortools.constraint_solver import pywrapcp, routing_enums_pb2
from app.config import CO2_FACTOR, FUEL_PRICE
from models.schemas import Route


def solve_candidate(s, matrix, mean, sigma, safety_z):
    ntrucks, norders = len(s.trucks), len(s.orders)
    if norders == 0:
        return []
    manager = pywrapcp.RoutingIndexManager(ntrucks+norders, ntrucks, list(range(ntrucks)), list(range(ntrucks)))
    routing = pywrapcp.RoutingModel(manager)
    demands = [0]*ntrucks + [o.weight_kg for o in s.orders]
    service = [0]*ntrucks + [o.service_time for o in s.orders]
    # Integer seconds; round travel UP and deadlines DOWN for conservative feasibility.
    def transit(a, b):
        i, j = manager.IndexToNode(a), manager.IndexToNode(b)
        return math.ceil(60*(service[i]+mean[i, j]+safety_z*sigma[i, j]))
    time_id = routing.RegisterTransitCallback(transit)
    routing.AddDimension(time_id, 86400, 172800, True, 'Time')
    time_dim = routing.GetDimensionOrDie('Time')
    for i, order in enumerate(s.orders):
        index = manager.NodeToIndex(ntrucks+i)
        time_dim.CumulVar(index).SetRange(math.ceil(order.window_start*60), math.floor(order.delivery_deadline*60))
        allowed = [v for v, t in enumerate(s.trucks) if t.availability and
                   t.capacity_kg >= order.weight_kg and order.region not in t.forbidden_regions]
        if not allowed:
            return None
        # Remove individual values: avoids the 9.15 Python Span binding issue.
        for vehicle in range(ntrucks):
            if vehicle not in allowed:
                routing.VehicleVar(index).RemoveValue(vehicle)
    demand_id = routing.RegisterUnaryTransitCallback(lambda index: demands[manager.IndexToNode(index)])
    routing.AddDimensionWithVehicleCapacity(demand_id, 0,
                                            [t.capacity_kg if t.availability else 0 for t in s.trucks], True, 'Load')
    callbacks = []
    for v, truck in enumerate(s.trucks):
        # Full-load fuel proxy in search; actual load-dependent fuel is recomputed after solving.
        def arc_cost(a, b, t=truck):
            i, j = manager.IndexToNode(a), manager.IndexToNode(b)
            km = matrix.distance[i, j]
            fuel = km/t.fuel_efficiency_kmpl
            priority = s.orders[j-ntrucks].priority if j >= ntrucks else 1
            objective = km*t.operating_cost_per_km + fuel*FUEL_PRICE + fuel*CO2_FACTOR*2 + sigma[i, j]*priority*4
            return round(objective*100)
        callbacks.append(arc_cost)
        routing.SetArcCostEvaluatorOfVehicle(routing.RegisterTransitCallback(arc_cost), v)
    params = pywrapcp.DefaultRoutingSearchParameters()
    params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION
    params.local_search_metaheuristic = routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
    params.time_limit.FromMilliseconds(650)
    params.log_search = False
    solution = routing.SolveWithParameters(params)
    if solution is None:
        return None
    routes = []
    for v, truck in enumerate(s.trucks):
        index, ids = routing.Start(v), []
        for _ in range(norders+2):
            if routing.IsEnd(index):
                break
            node = manager.IndexToNode(index)
            if node >= ntrucks:
                ids.append(s.orders[node-ntrucks].order_id)
            index = solution.Value(routing.NextVar(index))
        if ids:
            routes.append(Route(truck_id=truck.truck_id, order_ids=ids))
    return routes
