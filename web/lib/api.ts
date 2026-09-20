import type { BreakdownEvent, Plan, Scenario } from "./types";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/fleet/${path}`, { ...init, headers: { "Content-Type": "application/json", ...init?.headers } });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || "The request could not be completed.");
  return payload as T;
}

export const fleetApi = {
  demo: () => request<Scenario>("demo"),
  baseline: (scenario: Scenario, risk_budget: number) => request<Plan>("baseline", { method: "POST", body: JSON.stringify({ scenario, risk_budget }) }),
  optimize: (scenario: Scenario, risk_budget: number) => request<Plan>("optimize", { method: "POST", body: JSON.stringify({ scenario, risk_budget }) }),
  breakdown: (scenario: Scenario, plan: Plan, truck_id: string) => request<{ scenario: Scenario; event: BreakdownEvent; plan: Plan | null }>("breakdown", { method: "POST", body: JSON.stringify({ scenario, plan, truck_id, auto_reoptimize: true }) }),
};
