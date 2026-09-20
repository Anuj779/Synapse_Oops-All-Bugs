import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
import pandas as pd
import streamlit as st
from pydantic import ValidationError
from app.config import RISK_MODES
from app import service
from app.storage import recent
from data.generator import load_scenario, demo_scenario
from models.schemas import Scenario
from risk.model import load_model
from ui.components import show_plan, comparison

st.set_page_config(page_title='Adaptive Fleet AI', page_icon='🚚', layout='wide')
st.title('Adaptive Fleet AI')
st.markdown('### Risk-Budgeted Joint Route & Load Optimization')
st.caption('SYNAPSE 1.0 · AI IN AUTOMATION · PUNE → MUMBAI')
st.info('SIMULATED DEMO · Synthetic orders, road conditions and model training data. Predictions are not production-validated. Decision support only.')


def clear_plans():
    for key in ('baseline', 'optimized', 'event', 'changed', 'reoptimized'):
        st.session_state.pop(key, None)


if 'scenario' not in st.session_state:
    try:
        st.session_state.scenario = load_scenario()
    except (ValueError, OSError) as exc:
        st.error(f'Could not load local data: {exc}. Correct the CSV files before restarting.')
        st.stop()

with st.sidebar:
    st.markdown('## Dispatch controls')
    if st.button('Load demo mode', width='stretch'):
        st.session_state.scenario = demo_scenario()
        st.session_state.editor_version = st.session_state.get('editor_version', 0)+1
        clear_plans()
        st.rerun()
    mode = st.selectbox('Risk mode', list(RISK_MODES), index=1)
    if st.session_state.get('last_mode') != mode:
        st.session_state.risk_percent = round(RISK_MODES[mode]*100)
        st.session_state.last_mode = mode
    budget = st.slider('Max acceptable delay risk (%)', 1, 50, key='risk_percent')/100
    st.caption('Limit applies to the highest predicted lateness probability among all deliveries. It is not the chance of any fleet-wide failure.')
    auto = st.toggle('Automatically re-optimize on breakdown', value=True)
    st.caption('Turn off for the step-by-step presentation. The event still invalidates the old plan immediately.')
    st.markdown('**Planning assumptions**')
    st.write('08:00 departure · returns to depot · no split orders · pre-dispatch breakdown')
    st.caption('Economy tolerates more lateness risk. Reliable requires more time margin. Cost changes come from actual solves.')

s = st.session_state.scenario
counts = st.columns(4)
counts[0].metric('Pre-event available trucks', f'{sum(t.availability for t in s.trucks)} / {len(s.trucks)}')
counts[1].metric('Delivery orders', len(s.orders))
counts[2].metric('Freight', f'{sum(o.weight_kg for o in s.orders):,} kg')
counts[3].metric('Risk budget', f'{budget:.0%}')

with st.expander('1 · Fleet setup, orders and simulated conditions', expanded='optimized' not in st.session_state):
    st.caption('Edit and apply inputs before planning. Time windows are minutes after 08:00; 180 means 11:00. Save a scenario JSON to reuse or load via the API.')
    version = st.session_state.get('editor_version', 0)
    fleet_rows = [{**t.model_dump(exclude={'current_location', 'forbidden_regions'}),
                   'lat': t.current_location.lat, 'lon': t.current_location.lon,
                   'forbidden_regions': ','.join(t.forbidden_regions)} for t in s.trucks]
    order_rows = [{**o.model_dump(exclude={'location'}), 'lat': o.location.lat, 'lon': o.location.lon} for o in s.orders]
    with st.form('scenario_edit'):
        st.markdown('**Fleet setup**')
        fleet = st.data_editor(pd.DataFrame(fleet_rows), num_rows='dynamic', hide_index=True, width='stretch', key=f'fleet_{version}')
        st.markdown('**Orders**')
        orders = st.data_editor(pd.DataFrame(order_rows), num_rows='dynamic', hide_index=True, width='stretch', key=f'orders_{version}')
        a, b, c = st.columns(3)
        traffic = a.slider('Traffic severity', 0., 1., s.conditions.traffic_severity, .05)
        weather = b.slider('Weather severity', 0., 1., s.conditions.weather, .05)
        disruption = c.slider('Travel disruption factor', 0., 2., s.conditions.disruption_factor, .1)
        applied = st.form_submit_button('Apply setup')
    if applied:
        try:
            fleet_data, order_data = fleet.to_dict('records'), orders.to_dict('records')
            for row in fleet_data:
                row['current_location'] = {'lat': row.pop('lat'), 'lon': row.pop('lon')}
                row['forbidden_regions'] = [r.strip() for r in str(row['forbidden_regions'] or '').split(',') if r.strip()]
            for row in order_data:
                row['location'] = {'lat': row.pop('lat'), 'lon': row.pop('lon')}
            st.session_state.scenario = Scenario.model_validate(dict(trucks=fleet_data, orders=order_data,
                conditions=dict(traffic_severity=traffic, weather=weather, disruption_factor=disruption)))
            clear_plans()
            st.rerun()
        except (ValidationError, ValueError, TypeError) as exc:
            st.error(f'Invalid setup: {exc}')
    st.download_button('Download scenario JSON', s.model_dump_json(indent=2), 'scenario.json', 'application/json')

st.markdown('### 2 · Compare the fleet decisions')
col1, col2 = st.columns(2)
if col1.button('Generate Baseline', width='stretch'):
    try:
        with st.spinner('Building nearest feasible baseline…'):
            st.session_state.baseline = service.generate_baseline(s, budget)
    except (ValueError, OSError) as exc:
        st.error(str(exc))
if col2.button('Optimize Fleet', type='primary', width='stretch'):
    try:
        with st.spinner('Predicting risk, optimizing and validating…'):
            st.session_state.optimized = service.optimize_fleet(s, budget)
            for key in ('event', 'changed', 'reoptimized'):
                st.session_state.pop(key, None)
    except (ValueError, OSError) as exc:
        st.error(str(exc))

base, plan = st.session_state.get('baseline'), st.session_state.get('optimized')
if plan and plan.risk_budget != budget:
    st.warning('Risk budget changed. Optimize Fleet again to obtain a plan for the new limit. The displayed plan retains its original budget.')
if base and plan:
    comparison({'Baseline': base, 'Optimized': plan})
if base or plan:
    tabs = st.tabs(['Optimized plan', 'Baseline'])
    with tabs[0]:
        if plan:
            show_plan(s, plan)
        else:
            st.write('Choose Optimize Fleet to create a risk-constrained plan.')
    with tabs[1]:
        if base:
            show_plan(s, base)
        else:
            st.write('Generate the baseline to compare the same workload.')
else:
    st.write('Generate a baseline, then optimize the same orders with your accepted delivery-risk limit.')

st.markdown('### 3 · Disruption and fleet recovery')
if plan and plan.accepted and plan.routes and plan.risk_budget == budget:
    selected = st.selectbox('Truck to break down', [r.truck_id for r in plan.routes])
    if st.button('Simulate Breakdown', disabled='event' in st.session_state):
        with st.spinner('Invalidating the current plan and checking remaining capacity…'):
            changed, event, after = service.breakdown(s, plan, selected, auto)
            st.session_state.changed, st.session_state.event = changed, event
            if after is not None:
                st.session_state.reoptimized = after
    event = st.session_state.get('event')
    if event:
        st.error(f"EVENT · {event['truck_id']} unavailable. {event['stranded_orders']} deliveries stranded; the old plan is invalid.")
        st.write('Affected orders: '+', '.join(event['affected_order_ids']))
        st.write(f"Remaining capacity: {event['remaining_capacity_kg']:,} kg across {len(event['remaining_trucks'])} available trucks.")
        st.caption(event['timing'])
        st.caption('Without reassignment, affected orders cannot be served (100% non-service risk). This event status is separate from the ETA model’s lateness prediction.')
        if st.button('Re-optimize'):
            with st.spinner('Replanning all pending orders across the available fleet…'):
                st.session_state.reoptimized = service.reoptimize_fleet(st.session_state.changed, plan, budget)
        after = st.session_state.get('reoptimized')
        if after:
            st.markdown('**Before → breakdown → after**')
            comparison({'Before event': plan, 'After reoptimization': after})
            show_plan(st.session_state.changed, after)
        else:
            st.warning('Recovery is pending. Click Re-optimize to create a replacement plan.')
else:
    st.caption('Create an accepted plan at the current risk budget to enable the breakdown demonstration.')

with st.expander('Model, metrics and audit history'):
    st.write('Risk is calculated from predicted ETA, deadline slack and calibrated synthetic travel uncertainty. A shared route-delay factor conservatively adds leg standard deviations. This probability model needs real-world calibration.')
    st.write('The search uses operating cost + fuel cost + a CO₂ penalty + uncertainty penalty, subject to hard load, window, availability, regional and risk constraints. It is a bounded heuristic, not a proof of global optimality.')
    st.write('Fuel varies with remaining truck load. CO₂ uses a configurable demonstration factor of 2.68 kg/L. Empty kilometers include the return to the depot. Late deliveries are predicted, never observed outcomes.')
    if base or plan:
        st.json(load_model()[1])
    st.dataframe(pd.DataFrame(recent()), hide_index=True, width='stretch')
