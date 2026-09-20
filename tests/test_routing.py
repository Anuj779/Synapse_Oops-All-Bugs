import httpx
import pytest
from data.generator import demo_scenario
from routing.matrix import get_matrix


def test_valhalla_failure_falls_back(monkeypatch, tmp_path):
    def fail(*args, **kwargs):
        raise httpx.ConnectError('simulated outage')
    monkeypatch.setattr(httpx, 'post', fail)
    with pytest.warns(UserWarning, match='Demo Fallback'):
        matrix = get_matrix(demo_scenario(), 'http://localhost:8002', tmp_path)
    assert matrix.mode == 'Demo Fallback' and matrix.distance.shape == (17, 17)


def test_valhalla_success_is_cached(monkeypatch, tmp_path):
    s = demo_scenario()
    s.trucks, s.orders = s.trucks[:1], s.orders[:1]
    def response(*args, **kwargs):
        return httpx.Response(200, request=httpx.Request('POST', 'http://localhost'), json={'sources_to_targets': [
            [{'distance': 0, 'time': 0}, {'distance': 50, 'time': 3600}],
            [{'distance': 52, 'time': 3700}, {'distance': 0, 'time': 0}]]})
    monkeypatch.setattr(httpx, 'post', response)
    matrix = get_matrix(s, 'http://localhost:8002', tmp_path)
    assert matrix.mode == 'Valhalla' and matrix.minutes[0, 1] == 60
    def never(*args, **kwargs):
        raise AssertionError('Cache should avoid network calls')
    monkeypatch.setattr(httpx, 'post', never)
    assert get_matrix(s, 'http://localhost:8002', tmp_path).mode == 'Valhalla (cached)'
