from fastapi.testclient import TestClient
from app.main import app


def test_full_api_smoke():
    with TestClient(app) as client:
        assert client.get('/health').json()['status'] == 'ok'
        scenario = client.get('/demo').json()
        payload = {'scenario': scenario, 'risk_budget': .15}
        baseline = client.post('/baseline', json=payload)
        assert baseline.status_code == 200 and baseline.json()['accepted']
        optimized = client.post('/optimize', json=payload)
        assert optimized.status_code == 200 and optimized.json()['accepted']
        plan = optimized.json()
        event = client.post('/breakdown', json={'scenario': scenario, 'plan': plan,
                           'truck_id': plan['routes'][0]['truck_id'], 'auto_reoptimize': True})
        assert event.status_code == 200
        assert event.json()['event']['requires_reoptimization']
        assert event.json()['plan']['accepted']
        after = client.post('/reoptimize', json={'scenario': event.json()['scenario'], 'previous': plan, 'risk_budget': .15})
        assert after.status_code == 200 and after.json()['accepted']
        assert after.json()['metrics']['orders_served'] == 12
        assert client.get('/history').json()


def test_api_invalid_input():
    client = TestClient(app)
    assert client.post('/optimize', json={'scenario': {}, 'risk_budget': 1}).status_code == 422
