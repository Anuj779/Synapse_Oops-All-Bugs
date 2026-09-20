import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from app.config import START_HOUR

LABELS = {'distance_km': 'Distance (km)', 'fuel_litres': 'Fuel (L)', 'fuel_cost_inr': 'Fuel cost (INR)',
          'cost_inr': 'Total cost (INR)', 'co2_kg': 'CO₂ (kg)', 'max_delay_risk': 'Max delay risk (%)',
          'expected_late_deliveries': 'Expected late deliveries', 'late_deliveries': 'Mean-ETA late deliveries',
          'load_utilization': 'Used-truck load utilization (%)', 'empty_km': 'Empty return (km)',
          'trucks_used': 'Trucks used', 'orders_served': 'Orders served'}


def clock(minutes):
    total = round(minutes)+START_HOUR*60
    return f'{total//60:02}:{total%60:02}'


def comparison(plans):
    rows = []
    for key, label in LABELS.items():
        row = {'Metric': label}
        for name, plan in plans.items():
            value = plan.metrics.get(key)
            row[name] = round(value*(100 if key in ('max_delay_risk', 'load_utilization') else 1), 2) if value is not None else None
        rows.append(row)
    rows.append({'Metric': 'Solve time (seconds)', **{name: round(plan.elapsed_seconds, 3) for name, plan in plans.items()}})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
    if len(plans) == 2:
        (left, a), (right, b) = list(plans.items())
        if a.metrics.get('orders_served') == b.metrics.get('orders_served') and a.metrics.get('cost_inr', 0):
            change = (b.metrics['cost_inr']/a.metrics['cost_inr']-1)*100
            st.caption(f'{right} cost change vs {left}: {change:+.2f}%. Calculated from these runs; increases are shown honestly.')
        else:
            st.warning('Coverage differs. Cost savings are not comparable until the same orders are served.')


def route_chart(scenario, plan):
    orders = {o.order_id: o for o in scenario.orders}
    trucks = {t.truck_id: t for t in scenario.trucks}
    colors = ['#087e8b', '#d17320', '#7d57a4', '#3375b9', '#ae4565']
    fig = go.Figure()
    for i, route in enumerate(plan.routes):
        depot = trucks[route.truck_id].current_location
        points = [depot] + [orders[oid].location for oid in route.order_ids] + [depot]
        labels = [route.truck_id+' start'] + [oid+' · '+orders[oid].destination for oid in route.order_ids] + ['Return']
        fig.add_trace(go.Scatter(x=[p.lon for p in points], y=[p.lat for p in points], mode='lines+markers',
                                  name=route.truck_id, text=labels, hovertemplate='%{text}<extra>%{fullData.name}</extra>',
                                  line=dict(color=colors[i % len(colors)], width=2), marker=dict(size=8)))
    fig.update_layout(height=340, margin=dict(l=10, r=10, t=15, b=10),
                       xaxis_title='Longitude', yaxis_title='Latitude', paper_bgcolor='rgba(0,0,0,0)',
                       plot_bgcolor='rgba(0,0,0,0)', legend=dict(orientation='h'))
    st.plotly_chart(fig, width='stretch', key=plan.kind+'_routes')
    st.caption('Offline route schematic: straight connectors show visit sequence, not road geometry. Coordinates lie on the Pune–Mumbai corridor. Optional Valhalla uses OpenStreetMap-derived road data.')


def show_plan(scenario, plan):
    if plan.accepted:
        st.success('PASS · ' + ('Baseline capacity and predicted windows satisfied; risk is unconstrained.' if plan.kind == 'baseline' else 'All deliveries assigned and all feasibility checks passed.'))
    else:
        st.error('REJECT · ' + ' '.join(plan.reasons))
    st.caption(f'Routing mode: {plan.routing_mode} · Solve time: {plan.elapsed_seconds:.2f}s · Selected risk limit: {plan.risk_budget:.0%}')
    if not plan.metrics:
        if plan.iterations:
            st.dataframe(pd.DataFrame(plan.iterations), hide_index=True)
        return
    cols = st.columns(4)
    for col, label, value in zip(cols, ['Total cost', 'Max delay risk', 'Fuel', 'CO₂'],
                                  [f"₹{plan.metrics['cost_inr']:,.0f}", f"{plan.metrics['max_delay_risk']:.1%}",
                                   f"{plan.metrics['fuel_litres']:.1f} L", f"{plan.metrics['co2_kg']:.1f} kg"]):
        col.metric(label, value)
    rows = []
    orders = {o.order_id: o for o in scenario.orders}
    for route in plan.routes:
        for sequence, stop in enumerate(route.stops, 1):
            order = orders[stop.order_id]
            rows.append({'Truck': route.truck_id, 'Stop': sequence, 'Order': order.order_id,
                         'Destination': order.destination, 'Load (kg)': order.weight_kg,
                         'ETA': clock(stop.eta_minutes), 'Deadline': clock(order.delivery_deadline),
                         'Delay risk (%)': round(stop.delay_risk*100, 2)})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width='stretch')
    with st.expander('Truck loads, route sequence and costs', expanded=False):
        st.dataframe(pd.DataFrame([{'Truck': r.truck_id, 'Load (kg)': r.load_kg,
                                    'Route': ' → '.join(r.order_ids)+' → depot', 'Distance (km)': round(r.distance_km, 1),
                                    'Fuel (L)': round(r.fuel_litres, 1), 'Cost (INR)': round(r.cost_inr),
                                    'CO₂ (kg)': round(r.co2_kg, 1)} for r in plan.routes]), hide_index=True, width='stretch')
        route_chart(scenario, plan)
    if plan.explanations:
        st.markdown('**Why this plan?**')
        for explanation in plan.explanations:
            st.write('• ' + explanation)
    with st.expander('Risk loop and validation evidence'):
        st.json(plan.iterations)
    st.download_button('Download '+plan.kind+' plan', plan.model_dump_json(indent=2),
                       file_name=plan.kind+'_plan.json', mime='application/json', key='download_'+plan.kind)
