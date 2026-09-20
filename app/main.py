"""FastAPI interface. Streamlit uses the same service layer without requiring a server."""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app import service
from app.storage import recent
from data.generator import load_scenario
from models.schemas import Plan, Scenario
from simulation.disruptions import monitor_conditions

app = FastAPI(title='Adaptive Fleet AI', version='1.0.0',
              description='Synthetic demonstration. Risk-budgeted joint route and load optimization.')


class OptimizeRequest(BaseModel):
    scenario: Scenario
    risk_budget: float = Field(default=.15, gt=0, le=.5)


class BreakdownRequest(BaseModel):
    scenario: Scenario
    plan: Plan
    truck_id: str
    auto_reoptimize: bool = True


class ReplanRequest(OptimizeRequest):
    previous: Plan


@app.get('/health')
def health():
    return {'status': 'ok', 'simulation': True}


@app.get('/demo', response_model=Scenario)
def demo():
    return load_scenario()


@app.post('/baseline', response_model=Plan)
def baseline(request: OptimizeRequest):
    return service.generate_baseline(request.scenario, request.risk_budget)


@app.post('/optimize', response_model=Plan)
def optimize(request: OptimizeRequest):
    return service.optimize_fleet(request.scenario, request.risk_budget)


@app.post('/breakdown')
def breakdown(request: BreakdownRequest):
    try:
        scenario, event, plan = service.breakdown(request.scenario, request.plan, request.truck_id, request.auto_reoptimize)
        return {'scenario': scenario, 'event': event, 'plan': plan}
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post('/reoptimize', response_model=Plan)
def reoptimize(request: ReplanRequest):
    return service.reoptimize_fleet(request.scenario, request.previous, request.risk_budget)


@app.post('/monitor')
def monitor(request: ReplanRequest):
    result = monitor_conditions(request.scenario, request.previous, request.risk_budget)
    if result['plan'] is not None:
        service.record('reoptimized', result['plan'].model_dump())
    return result


@app.get('/history')
def history():
    return recent()
