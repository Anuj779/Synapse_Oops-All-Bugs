import { NextRequest } from "next/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
const ALLOWED = new Set(["health", "demo", "baseline", "optimize", "breakdown", "reoptimize", "monitor"]);

async function forward(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  const endpoint = path.join("/");
  if (!ALLOWED.has(endpoint)) return Response.json({ detail: "Unknown fleet endpoint." }, { status: 404 });
  const backend = (process.env.BACKEND_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");
  const headers = new Headers({ Accept: "application/json" });
  const init: RequestInit = { method: request.method, headers, cache: "no-store", signal: AbortSignal.timeout(20_000) };
  if (request.method !== "GET" && request.method !== "HEAD") {
    headers.set("Content-Type", "application/json");
    init.body = await request.text();
  }
  try {
    const response = await fetch(`${backend}/${endpoint}`, init);
    return new Response(await response.text(), { status: response.status, headers: { "Content-Type": response.headers.get("Content-Type") || "application/json" } });
  } catch {
    return Response.json({ detail: "The optimization service is unavailable. Start FastAPI locally or set BACKEND_API_URL in Vercel." }, { status: 503 });
  }
}

export const GET = forward;
export const POST = forward;
