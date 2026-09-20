import type { Plan, Scenario } from "@/lib/types";

type Bounds = { minLat: number; maxLat: number; minLon: number; maxLon: number };
type Point = { x: number; y: number };

function project(lat: number, lon: number, bounds: Bounds): Point {
  return {
    x: 8 + ((lon - bounds.minLon) / Math.max(bounds.maxLon - bounds.minLon, 0.001)) * 84,
    y: 90 - ((lat - bounds.minLat) / Math.max(bounds.maxLat - bounds.minLat, 0.001)) * 78,
  };
}

export function FleetMap({ scenario, plan, brokenTruck }: { scenario: Scenario; plan?: Plan; brokenTruck?: string }) {
  const locations = [...scenario.trucks.map((truck) => truck.current_location), ...scenario.orders.map((order) => order.location)];
  const bounds = {
    minLat: Math.min(...locations.map((point) => point.lat)),
    maxLat: Math.max(...locations.map((point) => point.lat)),
    minLon: Math.min(...locations.map((point) => point.lon)),
    maxLon: Math.max(...locations.map((point) => point.lon)),
  };
  const orders = new Map(scenario.orders.map((order) => [order.order_id, order]));
  const start = scenario.trucks[0].current_location;
  const depot = project(start.lat, start.lon, bounds);

  return (
    <div className="mapSurface">
      <svg viewBox="0 0 100 100" role="img" aria-label="Schematic route plan from Pune to Mumbai">
        <defs>
          <pattern id="map-grid" width="8" height="8" patternUnits="userSpaceOnUse">
            <path d="M 8 0 L 0 0 0 8" fill="none" stroke="currentColor" strokeWidth="0.15" opacity="0.16" />
          </pattern>
        </defs>
        <rect width="100" height="100" fill="url(#map-grid)" />
        {plan?.routes.map((route, index) => {
          const routePoints = [
            depot,
            ...route.order_ids.map((id) => orders.get(id)).filter(Boolean).map((order) => project(order!.location.lat, order!.location.lon, bounds)),
            depot,
          ];
          return (
            <polyline
              key={route.truck_id}
              points={routePoints.map((point) => `${point.x},${point.y}`).join(" ")}
              fill="none"
              stroke={route.truck_id === brokenTruck ? "#9c9f99" : "#c9511a"}
              strokeWidth={1.45 + index * 0.22}
              strokeOpacity={0.9 - index * 0.13}
              strokeDasharray={route.truck_id === brokenTruck ? "2 2" : undefined}
              vectorEffect="non-scaling-stroke"
            />
          );
        })}
        <circle cx={depot.x} cy={depot.y} r="2.1" className="depotDot" />
        {scenario.orders.map((order) => {
          const point = project(order.location.lat, order.location.lon, bounds);
          return <circle key={order.order_id} cx={point.x} cy={point.y} r="1.35" className="orderDot" />;
        })}
      </svg>
      <div className="mapLabel mapLabelPune">Pune depot</div>
      <div className="mapLabel mapLabelMumbai">Mumbai region</div>
      {!plan && <div className="mapEmpty">Generate a plan to draw vehicle routes</div>}
    </div>
  );
}
