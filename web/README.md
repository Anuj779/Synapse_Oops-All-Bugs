# Adaptive Fleet React interface

This is the Vercel-ready Next.js interface for Adaptive Fleet AI. It keeps the verified Python optimizer as the source of truth and sends all fleet actions through a same-origin Next.js proxy.

## Run locally

Start the Python API from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Start the React interface in a second terminal:

```powershell
cd web
npm install
npm run dev
```

Open `http://localhost:3000`. The frontend defaults to `http://127.0.0.1:8000` for the API.

## Deploy the frontend to Vercel

1. Import the GitHub repository into Vercel.
2. Set **Root Directory** to `web`.
3. Keep the detected framework as **Next.js** and the normal build command `npm run build`.
4. Add `BACKEND_API_URL` with the public HTTPS address of the deployed Python FastAPI service.
5. Deploy, then open the deployment and verify that the optimization service indicator and generated fleet plan load.

The Python optimizer cannot be hosted inside this Next.js deployment because XGBoost and Google OR-Tools run in the separate backend process. Host the FastAPI service on a Python-capable provider, then use its URL in `BACKEND_API_URL`.

## Validation

```powershell
npm run lint
npm run build
```

The interface includes loading, service-error, accepted-plan, infeasible-plan, changed-risk and breakdown-recovery states. It is responsive for desktop, tablet and mobile layouts.
