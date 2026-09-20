"""Deterministic, fictional Pune–Mumbai freight data. Never overwrite existing CSVs."""
import json
from pathlib import Path
import pandas as pd
from app.config import DATA_DIR
from models.schemas import Conditions, Location, Order, Scenario, Truck

DEPOT = Location(lat=18.6298, lon=73.7997)


def demo_scenario() -> Scenario:
    trucks = [Truck(truck_id=f'T{i+1}', capacity_kg=cap, current_location=DEPOT,
                    fuel_efficiency_kmpl=eff, operating_cost_per_km=cost)
              for i, (cap, eff, cost) in enumerate([(4000, 5.5, 9), (3500, 6, 8),
                                                   (3000, 6.5, 7), (2500, 7, 6), (4500, 5, 10)])]
    points = [('Lonavala', 18.7546, 73.4062), ('Khopoli', 18.7888, 73.3433),
              ('Khalapur', 18.8348, 73.2804), ('Panvel', 18.9894, 73.1175),
              ('Kalamboli', 19.0328, 73.1012), ('Taloja', 19.0715, 73.1132),
              ('Belapur', 19.0189, 73.0395), ('Nerul', 19.033, 73.0181),
              ('Vashi', 19.0771, 72.9986), ('Turbhe', 19.075, 73.017),
              ('Airoli', 19.1579, 72.9936), ('Thane', 19.2183, 72.9781)]
    orders = [Order(order_id=f'O{i+1:02}', destination=name, location=Location(lat=lat, lon=lon),
                    weight_kg=[650, 900, 750, 1100, 800, 950, 700, 850, 1000, 600, 800, 900][i],
                    delivery_deadline=[115, 130, 145, 175, 193, 200, 201, 210, 220, 225, 245, 260][i],
                    service_time=10, priority=2 if i > 8 else 1)
              for i, (name, lat, lon) in enumerate(points)]
    return Scenario(trucks=trucks, orders=orders)


def ensure_demo_files(directory: Path = DATA_DIR):
    directory.mkdir(parents=True, exist_ok=True)
    s = demo_scenario()
    for name, rows in [('trucks', s.trucks), ('orders', s.orders), ('road_conditions', [s.conditions])]:
        path = directory / f'{name}.csv'
        if not path.exists():
            records = []
            for row in rows:
                record = row.model_dump()
                for key, value in record.items():
                    if isinstance(value, (dict, list)):
                        record[key] = json.dumps(value)
                records.append(record)
            pd.DataFrame(records).to_csv(path, index=False)


def load_scenario(directory: Path = DATA_DIR) -> Scenario:
    ensure_demo_files(directory)
    def read(name, cls):
        records = pd.read_csv(directory / f'{name}.csv', keep_default_na=False).to_dict('records')
        for record in records:
            for key in ('current_location', 'location', 'forbidden_regions'):
                if key in record:
                    record[key] = json.loads(record[key])
        return [cls.model_validate(record) for record in records]
    return Scenario(trucks=read('trucks', Truck), orders=read('orders', Order),
                    conditions=read('road_conditions', Conditions)[0])
