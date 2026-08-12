# Water Leak Detection Service

A FastAPI, browser, and command-line object-detection service for visible
water leaks. Every entry point uses one fixed Torch ensemble from the project
root:

- `best.pt` is the general detector. Its classes must be exactly, in order:
  `pipe burst`, `water accumulation`, `water drop`.
- `waterAccubest.pt` is the legacy specialist. Its only class must be exactly
  `water damage`.

The service exposes two independent model roles. `WaterAccumulation` runs only
`waterAccubest.pt` and exposes its `water damage` output as `water
accumulation`. `WaterDetection` runs only the three-class `best.pt` model.
There is no combined fallback model. Model files, roles, and paths are owned by
the service.

## Install

Python 3.11 and the pinned Python dependencies are required. Node.js 22 is
used to validate and build the React frontend.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install torch==2.13.0 torchvision==0.28.0 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements-dev.txt
cd frontend
npm.cmd ci
npm.cmd run build
cd ..
```

`requirements.txt` contains service dependencies; `requirements-dev.txt` adds
test and training/development dependencies.

## Train the dataset

Validate the dataset before starting a run:

```powershell
python scripts/audit_dataset.py
```

Annotation definitions and split rules are documented in
`docs/annotation-policy.md`.

Recoverable cleanup is available when an audit reports invalid boxes, exact
duplicates, EXIF orientation, or MPO containers:

```powershell
python scripts/audit_dataset.py --fix
```

The repair command moves duplicates and copies originals into
`.scratch/dataset-quarantine/` before changing the active dataset. It refuses
to reuse an existing quarantine directory, preventing accidental overwrite of
the recovery copy.

```powershell
python -c "from ultralytics.cfg import entrypoint; entrypoint()" detect train model=yolov8n.pt data=dataset/data.yaml epochs=50 imgsz=640 batch=8 device=cpu workers=0 project=runs name=water-detection
```

The general detector's trained weights are created under
`runs/water-detection/weights/`. Install a replacement general model at the
runtime-owned path with:

```powershell
Copy-Item runs/water-detection/weights/best.pt best.pt
```

Keep `waterAccubest.pt` at the repository root as the one-class specialist
model. Back up existing root-level model files before replacing them.

## Command line

Run a selected model role on one image:

```powershell
python main.py --image test1.jpg --conf 0.25 --device cpu
# Add --model water_accumulation when the specialist is needed.
```

The command prints a JSON array. An empty array means no detection reached the
selected confidence threshold. General detections, including overlapping
detections of different classes, are retained.

## Web interface and API

Build the React frontend after changing it, then start FastAPI on CPU:

```powershell
cd frontend
npm.cmd run build
cd ..
$env:YOLO_DEVICE = "cpu"
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000
```

For frontend development with hot module replacement, run FastAPI as above and
run `npm.cmd run dev` from `frontend` in a second terminal. Vite proxies
`/detect` and `/health` to FastAPI.

Open:

- <http://127.0.0.1:8000/> for the visual image/video interface.
- <http://127.0.0.1:8000/docs> for Swagger.
- <http://127.0.0.1:8000/health> for readiness status.

The service creates one runtime for the process and reuses the two Torch
models. `YOLO_DEVICE` selects the inference device; upload limits,
timeouts, and concurrency are server-owned settings.

## Tests and CI

Run the frontend checks and the Python unit/API suite:

```powershell
cd frontend
npm.cmd run lint
npm.cmd run typecheck
npm.cmd test
npm.cmd run build
cd ..
python -m unittest discover -s tests -p "test_*.py"
```

Run the focused fixed-runtime tests directly:

```powershell
python -m unittest tests.test_detection_runtime tests.test_ensemble_runtime
```

## Benchmark

```powershell
python benchmark.py --image test1.jpg --conf 0.25 --device cpu --warmup 2 --runs 10
```

The benchmark measures cold and cached inference through one reused fixed
ensemble. See [benchmark.md](benchmark.md).

## Docker

Build and run the CPU-only service:

```powershell
docker build -t water-leak-service .
docker run --rm --init --read-only `
  --tmpfs /tmp:rw,noexec,nosuid,size=64m `
  --cap-drop ALL `
  --security-opt no-new-privileges:true `
  --memory 4g --cpus 2 `
  -p 8000:8000 `
  -e YOLO_DEVICE=cpu `
  water-leak-service
```

The image builds the frontend, includes `best.pt` and `waterAccubest.pt`,
runs as UID/GID `10001`, and exposes a `/health` health check. Then open
<http://127.0.0.1:8000/>. See [deploy.md](deploy.md) for smoke verification
and hardened deployment details.

## Project layout

```text
api/                         FastAPI routes and built-frontend serving
frontend/src/components/     React interface modules
frontend/src/lib/            Typed detection, review, ZIP, and video modules
frontend/src/types.ts        Shared frontend domain types
frontend/                    Vite, TypeScript, ESLint, and Vitest configuration
config/                      CLI and server-owned configuration
models/                      Detection result data structure
service/                     Fixed-model runtime and ensemble logic
utils/                       Logging and application exceptions
tests/                       Unit, API, UI, and opt-in model tests
scripts/audit_dataset.py     Dataset validation and repair
cli.py                       Command-line argument parsing
main.py                      Command-line entry point
benchmark.py                 Runtime timing benchmark
Dockerfile                   CPU container deployment
requirements.txt             Pinned service dependencies
requirements-dev.txt         Pinned development dependencies
```
