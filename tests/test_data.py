from data.generator import demo_scenario, load_scenario
import pytest
from pydantic import ValidationError


def test_demo_loads_without_overwrite(tmp_path):
    s = load_scenario(tmp_path)
    assert len(s.trucks) == 5 and len(s.orders) == 12
    assert s == demo_scenario()
    path = tmp_path / 'orders.csv'
    original = path.read_bytes()
    load_scenario(tmp_path)
    assert path.read_bytes() == original


def test_invalid_window_and_duplicate_rejected():
    s = demo_scenario().model_dump()
    s['orders'][0]['window_start'] = 500
    with pytest.raises(ValidationError):
        type(demo_scenario()).model_validate(s)
    s = demo_scenario().model_dump()
    s['trucks'][1]['truck_id'] = 'T1'
    with pytest.raises(ValidationError):
        type(demo_scenario()).model_validate(s)
