import numpy as np
import pytest
from data.generator import demo_scenario
from models.schemas import Route
from routing.matrix import Matrix
from metrics.calculations import evaluate
from app.config import CO2_FACTOR, FUEL_PRICE


def test_metrics_hand_calculated_single_delivery():
    s = demo_scenario()
    s.trucks, s.orders = s.trucks[:1], s.orders[:1]
    t, o = s.trucks[0], s.orders[0]
    t.capacity_kg, t.fuel_efficiency_kmpl, t.operating_cost_per_km = 1000, 5, 10
    o.weight_kg = 500
    matrix = Matrix(np.array([[0., 100.], [100., 0.]]), np.array([[0., 80.], [80., 0.]]), 'test')
    p = evaluate(s, [Route(truck_id=t.truck_id, order_ids=[o.order_id])], matrix, matrix.minutes, np.zeros((2, 2)))
    assert p.metrics['fuel_litres'] == pytest.approx(100/5*.9+100/5*.8)
    assert p.metrics['distance_km'] == 200 and p.metrics['empty_km'] == 100
    assert p.metrics['cost_inr'] == pytest.approx(2000+34*FUEL_PRICE)
    assert p.metrics['co2_kg'] == pytest.approx(34*CO2_FACTOR)
    assert p.metrics['load_utilization'] == .5
    assert p.metrics['late_deliveries'] == 0
