import numpy as np
from data.generator import demo_scenario
from risk.model import historical_data, predict_matrix, load_model
from routing.matrix import fallback
from metrics.calculations import lateness_risk


def test_reproducible_data_and_prediction():
    assert historical_data().equals(historical_data())
    s = demo_scenario()
    mean, sd = predict_matrix(fallback(s), s.conditions)
    assert np.isfinite(mean).all() and (sd >= 0).all()
    assert np.diag(mean).sum() == 0
    assert load_model()[1]['test_rows'] == 900
    assert np.array_equal(mean, predict_matrix(fallback(s), s.conditions)[0])


def test_risk_responds_to_slack():
    assert lateness_risk(100, 10, 100) == .5
    assert lateness_risk(100, 10, 130) < .01
    assert lateness_risk(100, 10, 110) > lateness_risk(100, 10, 120)
