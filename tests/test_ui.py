from streamlit.testing.v1 import AppTest
from app.config import ROOT


def test_streamlit_complete_demo():
    app = AppTest.from_file(ROOT / 'ui/dashboard.py', default_timeout=30).run()
    assert not app.exception
    def press(label):
        next(b for b in app.button if b.label == label).click().run()
        assert not app.exception
    press('Load demo mode')
    press('Generate Baseline')
    assert app.session_state['baseline'].accepted
    press('Optimize Fleet')
    assert app.session_state['optimized'].accepted
    press('Simulate Breakdown')
    assert app.session_state['event']['requires_reoptimization']
    assert app.session_state['reoptimized'].accepted
    press('Re-optimize')
    assert app.session_state['reoptimized'].metrics['orders_served'] == 12
    press('Load demo mode')
    assert 'optimized' not in app.session_state


def test_manual_recovery_and_changed_risk_budget():
    app = AppTest.from_file(ROOT / 'ui/dashboard.py', default_timeout=30).run()
    next(t for t in app.toggle if t.label == 'Automatically re-optimize on breakdown').set_value(False).run()
    next(b for b in app.button if b.label == 'Optimize Fleet').click().run()
    assert app.session_state['optimized'].accepted
    next(b for b in app.button if b.label == 'Simulate Breakdown').click().run()
    assert 'reoptimized' not in app.session_state
    assert any('Recovery is pending' in w.value for w in app.warning)
    next(b for b in app.button if b.label == 'Re-optimize').click().run()
    assert app.session_state['reoptimized'].accepted
    next(slider for slider in app.slider if slider.label == 'Max acceptable delay risk (%)').set_value(5).run()
    assert any('Risk budget changed' in w.value for w in app.warning)
    assert not any(b.label == 'Simulate Breakdown' for b in app.button)
    assert not app.exception
