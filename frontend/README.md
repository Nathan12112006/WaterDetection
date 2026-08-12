# WaterLeak React frontend

This Vite application is the browser interface for the FastAPI detection
service. It uses React and strict TypeScript. FastAPI remains responsible for
model verification and inference; the frontend owns media sampling, review
state, dataset export, and rendering.

## Development

Start FastAPI from the repository root:

```powershell
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

Vite proxies `/detect` and `/health` to FastAPI. Open the URL printed by Vite.

## Validation and production build

```powershell
npm.cmd run lint
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
```

The production build is written to `frontend/dist`. FastAPI serves that build
at `/`, and Docker creates it automatically in a Node build stage.
