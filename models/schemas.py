from pydantic import BaseModel, Field, model_validator


class Location(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class Truck(BaseModel):
    truck_id: str = Field(min_length=1)
    capacity_kg: int = Field(gt=0, le=100000)
    current_location: Location
    fuel_efficiency_kmpl: float = Field(gt=0, le=50)
    operating_cost_per_km: float = Field(ge=0, le=1000)
    availability: bool = True
    forbidden_regions: list[str] = Field(default_factory=list)


class Order(BaseModel):
    order_id: str = Field(min_length=1)
    destination: str
    location: Location
    weight_kg: int = Field(gt=0, le=100000)
    window_start: float = Field(default=0, ge=0, le=1440)
    delivery_deadline: float = Field(gt=0, le=1440)
    service_time: float = Field(default=10, ge=0, le=240)
    priority: int = Field(default=1, ge=1, le=5)
    region: str = 'corridor'

    @model_validator(mode='after')
    def window_valid(self):
        if self.window_start > self.delivery_deadline:
            raise ValueError('Window start must not exceed deadline')
        return self


class Conditions(BaseModel):
    traffic_severity: float = Field(default=.45, ge=0, le=1)
    weather: float = Field(default=0.0, ge=0, le=1)
    disruption_factor: float = Field(default=0.0, ge=0, le=2)


class Scenario(BaseModel):
    trucks: list[Truck] = Field(min_length=1, max_length=10)
    orders: list[Order] = Field(max_length=30)
    conditions: Conditions = Field(default_factory=Conditions)
    simulated: bool = True

    @model_validator(mode='after')
    def unique_ids(self):
        for name in ('trucks', 'orders'):
            ids = [getattr(x, 'truck_id' if name == 'trucks' else 'order_id') for x in getattr(self, name)]
            if len(ids) != len(set(ids)):
                raise ValueError(f'Duplicate IDs in {name}')
        return self


class Stop(BaseModel):
    order_id: str
    eta_minutes: float
    delay_risk: float


class Route(BaseModel):
    truck_id: str
    order_ids: list[str]
    stops: list[Stop] = Field(default_factory=list)
    load_kg: int = 0
    distance_km: float = 0
    empty_km: float = 0
    fuel_litres: float = 0
    cost_inr: float = 0
    co2_kg: float = 0


class Plan(BaseModel):
    kind: str
    routes: list[Route] = Field(default_factory=list)
    accepted: bool = False
    reasons: list[str] = Field(default_factory=list)
    risk_budget: float = Field(ge=0, le=.5)
    metrics: dict[str, float] = Field(default_factory=dict)
    iterations: list[dict] = Field(default_factory=list)
    explanations: list[str] = Field(default_factory=list)
    routing_mode: str = 'Demo Fallback'
    elapsed_seconds: float = 0
