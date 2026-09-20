"use client";

import {
  Button,
  Menu,
  MenuItem,
  MenuList,
  MenuPopover,
  MenuTrigger,
  ProgressBar,
  Skeleton,
  SkeletonItem,
  Slider,
  Tab,
  TabList,
  Tooltip,
  type SelectTabData,
  type SelectTabEvent,
} from "@fluentui/react-components";
import {
  ArrowClockwise20Regular,
  BoxMultiple20Regular,
  ChevronDown20Regular,
  DataTrending20Regular,
  MoreHorizontal20Regular,
  ShieldCheckmark20Regular,
  VehicleTruck20Regular,
  Warning20Regular,
} from "@fluentui/react-icons";
import { useCallback, useEffect, useMemo, useState } from "react";
import { fleetApi } from "@/lib/api";
import type { BreakdownEvent, Plan, RiskMode, Scenario } from "@/lib/types";
import { FleetMap } from "./fleet-map";
import { Providers } from "./providers";

const MODES: Record<RiskMode, number> = { Economy: 35, Balanced: 15, Reliable: 5 };

function money(value = 0) {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value);
}

function clock(minutes: number) {
  const total = 8 * 60 + Math.round(minutes);
  return `${String(Math.floor(total / 60)).padStart(2, "0")}:${String(total % 60).padStart(2, "0")}`;
}

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong><small>{note}</small></div>;
}

function Workspace() {
  const [scenario, setScenario] = useState<Scenario>();
  const [baseline, setBaseline] = useState<Plan>();
  const [plan, setPlan] = useState<Plan>();
  const [riskMode, setRiskMode] = useState<RiskMode | "Custom">("Balanced");
  const [riskPercent, setRiskPercent] = useState(MODES.Balanced);
  const [selectedView, setSelectedView] = useState("routes");
  const [loading, setLoading] = useState(true);
  const [planning, setPlanning] = useState(false);
  const [recovering, setRecovering] = useState(false);
  const [error, setError] = useState<string>();
  const [event, setEvent] = useState<BreakdownEvent>();
  const [preEventPlan, setPreEventPlan] = useState<Plan>();

  const runPlanning = useCallback(async (input: Scenario, risk: number) => {
    setPlanning(true);
    setError(undefined);
    setEvent(undefined);
    setPreEventPlan(undefined);
    try {
      const [nextBaseline, nextPlan] = await Promise.all([
        fleetApi.baseline(input, risk / 100),
        fleetApi.optimize(input, risk / 100),
      ]);
      setBaseline(nextBaseline);
      setPlan(nextPlan);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Planning failed.");
    } finally {
      setPlanning(false);
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function initialize() {
      try {
        const demo = await fleetApi.demo();
        if (cancelled) return;
        setScenario(demo);
        await runPlanning(demo, MODES.Balanced);
      } catch (requestError) {
        if (!cancelled) setError(requestError instanceof Error ? requestError.message : "Demo data could not be loaded.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    initialize();
    return () => { cancelled = true; };
  }, [runPlanning]);

  const orders = useMemo(() => new Map(scenario?.orders.map((order) => [order.order_id, order]) || []), [scenario]);
  const trucks = useMemo(() => new Map(scenario?.trucks.map((truck) => [truck.truck_id, truck]) || []), [scenario]);
  const costDelta = baseline && plan ? (plan.metrics.cost_inr / baseline.metrics.cost_inr - 1) * 100 : 0;
  const stale = !!plan && Math.round(plan.risk_budget * 100) !== riskPercent;

  function chooseMode(mode: RiskMode) {
    setRiskMode(mode);
    setRiskPercent(MODES[mode]);
  }

  async function simulateBreakdown(truckId: string) {
    if (!scenario || !plan) return;
    setRecovering(true);
    setError(undefined);
    setPreEventPlan(plan);
    try {
      const result = await fleetApi.breakdown(scenario, plan, truckId);
      setScenario(result.scenario);
      setEvent(result.event);
      if (result.plan) setPlan(result.plan);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Recovery planning failed.");
    } finally {
      setRecovering(false);
    }
  }

  if (loading) {
    return <main className="loadingShell"><Skeleton aria-label="Loading dispatcher workspace"><SkeletonItem className="loadingHeader" /><div className="loadingGrid"><SkeletonItem /><SkeletonItem /></div><SkeletonItem className="loadingMetrics" /></Skeleton></main>;
  }

  return (
    <main className="appShell">
      <header className="topbar">
        <div className="brandBlock"><div className="brandMark"><VehicleTruck20Regular /></div><div><strong>Adaptive Fleet</strong><span>Operations control</span></div></div>
        <div className="topbarMeta"><span className="simulationLabel">Simulated data</span><span className="serviceStatus"><i /> Optimization service</span>
          <Menu><MenuTrigger disableButtonEnhancement><Button appearance="subtle" icon={<MoreHorizontal20Regular />} aria-label="More options" /></MenuTrigger><MenuPopover><MenuList><MenuItem onClick={() => scenario && runPlanning(scenario, riskPercent)}>Refresh plan</MenuItem></MenuList></MenuPopover></Menu>
        </div>
      </header>

      <section className="commandHeader">
        <div><p className="contextLine">Pune depot to Mumbai region</p><h1>Plan today&apos;s fleet</h1><p>Choose the delivery risk you can accept. The system assigns trucks, loads and stops together.</p></div>
        <div className="fleetSnapshot"><span><VehicleTruck20Regular /> {scenario?.trucks.filter((truck) => truck.availability).length || 0} trucks ready</span><span><BoxMultiple20Regular /> {scenario?.orders.length || 0} orders</span><span><DataTrending20Regular /> {scenario?.conditions.traffic_severity.toFixed(2)} traffic</span></div>
      </section>

      {error && <div className="errorBanner" role="alert"><Warning20Regular /><div><strong>We could not update the fleet plan</strong><span>{error}</span></div><Button appearance="transparent" onClick={() => scenario && runPlanning(scenario, riskPercent)}>Try again</Button></div>}

      <section className="decisionGrid">
        <div className="mapPanel">
          <div className="panelHeading"><div><span>Live plan</span><h2>Fleet movement</h2></div><span className="routingMode">{plan?.routing_mode || "Awaiting route"}</span></div>
          {scenario && <FleetMap scenario={scenario} plan={plan} brokenTruck={event?.truck_id} />}
          <div className="mapFooter"><span><i className="legendRoute" /> Active route</span><span><i className="legendStop" /> Delivery</span><span>{plan?.metrics.orders_served || 0} of {scenario?.orders.length || 0} orders assigned</span></div>
        </div>

        <aside className="controlPanel">
          <div className="panelHeading"><div><span>Decision controls</span><h2>Risk budget</h2></div><ShieldCheckmark20Regular /></div>
          <p className="controlCopy">Maximum predicted lateness risk for any delivery.</p>
          <div className="modeSelector" role="group" aria-label="Risk mode">
            {(Object.keys(MODES) as RiskMode[]).map((mode) => <button key={mode} className={riskMode === mode ? "active" : ""} onClick={() => chooseMode(mode)}><strong>{mode}</strong><span>{MODES[mode]}% max</span></button>)}
          </div>
          <div className="sliderBlock"><div><label htmlFor="risk-slider">Custom risk limit</label><output>{riskPercent}%</output></div><Slider id="risk-slider" min={1} max={50} value={riskPercent} onChange={(_, data) => { setRiskPercent(data.value); setRiskMode("Custom"); }} /><div className="sliderScale"><span>Reliable</span><span>Economy</span></div></div>
          <Button appearance="primary" size="large" icon={planning ? undefined : <ArrowClockwise20Regular />} disabled={!scenario || planning} onClick={() => scenario && runPlanning(scenario, riskPercent)} className="primaryAction">{planning ? "Building fleet plan..." : stale ? "Apply new risk limit" : "Recalculate plan"}</Button>
          {planning && <ProgressBar thickness="medium" aria-label="Optimizing fleet" />}
          <div className={`decisionStatus ${plan?.accepted ? "accepted" : "rejected"}`}><span>{plan?.accepted ? <ShieldCheckmark20Regular /> : <Warning20Regular />}</span><div><strong>{plan?.accepted ? "Plan accepted" : "Plan needs attention"}</strong><p>{plan?.accepted ? `${(plan.metrics.max_delay_risk * 100).toFixed(1)}% maximum risk within the ${Math.round(plan.risk_budget * 100)}% limit.` : plan?.reasons[0] || "Generate a plan to begin."}</p></div></div>
        </aside>
      </section>

      {event && <section className="eventBanner" aria-live="polite"><div className="eventIcon"><Warning20Regular /></div><div><span>Recovery complete</span><strong>{event.truck_id} removed from service</strong><p>{event.stranded_orders} affected deliveries reassigned across {event.remaining_trucks.length} available trucks.</p></div><div className="eventMetric"><span>Remaining capacity</span><strong>{event.remaining_capacity_kg.toLocaleString("en-IN")} kg</strong></div></section>}

      <section className="metricStrip" aria-label="Fleet performance summary">
        <Metric label="Total cost" value={money(plan?.metrics.cost_inr)} note={baseline ? `${costDelta > 0 ? "+" : ""}${costDelta.toFixed(1)}% vs baseline` : "Awaiting baseline"} />
        <Metric label="Distance" value={`${(plan?.metrics.distance_km || 0).toFixed(0)} km`} note={`${(plan?.metrics.empty_km || 0).toFixed(0)} km empty return`} />
        <Metric label="Fuel" value={`${(plan?.metrics.fuel_litres || 0).toFixed(1)} L`} note={`${(plan?.metrics.co2_kg || 0).toFixed(0)} kg CO₂`} />
        <Metric label="Fleet load" value={`${((plan?.metrics.load_utilization || 0) * 100).toFixed(0)}%`} note={`${plan?.metrics.trucks_used || 0} trucks in plan`} />
        <Metric label="Solve time" value={`${(plan?.elapsed_seconds || 0).toFixed(2)} s`} note={`${plan?.iterations.length || 0} bounded attempts`} />
      </section>

      <section className="detailsSection">
        <div className="detailsHeader">
          <TabList selectedValue={selectedView} onTabSelect={(_: SelectTabEvent, data: SelectTabData) => setSelectedView(String(data.value))}><Tab value="routes">Truck routes</Tab><Tab value="orders">Order manifest</Tab><Tab value="reasoning">Why this plan</Tab></TabList>
          {plan?.accepted && !event && <Menu><MenuTrigger disableButtonEnhancement><Button appearance="outline" icon={<Warning20Regular />}>Simulate breakdown <ChevronDown20Regular /></Button></MenuTrigger><MenuPopover><MenuList>{plan.routes.map((route) => <MenuItem key={route.truck_id} onClick={() => simulateBreakdown(route.truck_id)}>Break down {route.truck_id}</MenuItem>)}</MenuList></MenuPopover></Menu>}
          {recovering && <span className="recoveringText"><ArrowClockwise20Regular /> Reoptimizing...</span>}
        </div>

        {selectedView === "routes" && <div className="routeGrid">{plan?.routes.map((route) => {
          const truck = trucks.get(route.truck_id);
          const load = Math.round((route.load_kg / (truck?.capacity_kg || route.load_kg)) * 100);
          return <article className="routeCard" key={route.truck_id}>
            <div className="routeTop"><div><span className="truckIcon"><VehicleTruck20Regular /></span><div><strong>{route.truck_id}</strong><small>{route.order_ids.length} deliveries</small></div></div><strong>{load}% load</strong></div>
            <div className="capacityTrack"><span style={{ width: `${Math.min(100, load)}%` }} /></div>
            <div className="stopSequence">{route.stops.map((stop, index) => <div key={stop.order_id}><span>{index + 1}</span><div><strong>{orders.get(stop.order_id)?.destination}</strong><small>{stop.order_id} · ETA {clock(stop.eta_minutes)}</small></div><Tooltip content={`${(stop.delay_risk * 100).toFixed(1)}% predicted lateness risk`} relationship="label"><em>{(stop.delay_risk * 100).toFixed(1)}%</em></Tooltip></div>)}</div>
            <div className="routeBottom"><span>{route.distance_km.toFixed(0)} km</span><span>{route.fuel_litres.toFixed(1)} L</span><strong>{money(route.cost_inr)}</strong></div>
          </article>;
        })}</div>}

        {selectedView === "orders" && <div className="tableWrap"><table><thead><tr><th>Order</th><th>Destination</th><th>Weight</th><th>Truck</th><th>ETA</th><th>Deadline</th><th>Risk</th></tr></thead><tbody>{plan?.routes.flatMap((route) => route.stops.map((stop) => { const order = orders.get(stop.order_id); return <tr key={stop.order_id}><td><strong>{stop.order_id}</strong></td><td>{order?.destination}</td><td>{order?.weight_kg.toLocaleString("en-IN")} kg</td><td>{route.truck_id}</td><td>{clock(stop.eta_minutes)}</td><td>{order ? clock(order.delivery_deadline) : ""}</td><td><span className={stop.delay_risk <= plan.risk_budget ? "riskOk" : "riskHigh"}>{(stop.delay_risk * 100).toFixed(1)}%</span></td></tr>; }))}</tbody></table></div>}

        {selectedView === "reasoning" && <div className="reasoningGrid"><div><h3>Decision evidence</h3>{plan?.explanations.map((item, index) => <div className="reasonItem" key={item}><span>{index + 1}</span><p>{item}</p></div>)}</div><aside><h3>Plan comparison</h3><dl><div><dt>Baseline cost</dt><dd>{money(baseline?.metrics.cost_inr)}</dd></div><div><dt>Accepted cost</dt><dd>{money(plan?.metrics.cost_inr)}</dd></div><div><dt>Baseline risk</dt><dd>{((baseline?.metrics.max_delay_risk || 0) * 100).toFixed(1)}%</dd></div><div><dt>Accepted risk</dt><dd>{((plan?.metrics.max_delay_risk || 0) * 100).toFixed(1)}%</dd></div>{preEventPlan && <div><dt>Pre-event cost</dt><dd>{money(preEventPlan.metrics.cost_inr)}</dd></div>}</dl></aside></div>}
      </section>

      <footer><span>Decision-support prototype using synthetic demonstration data.</span><span>Risk predictions are not production validated.</span></footer>
    </main>
  );
}

export function FleetWorkspace() {
  return <Providers><Workspace /></Providers>;
}
