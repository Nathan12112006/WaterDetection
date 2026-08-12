<!-- codex-workflow-bootstrap-template -->
# Project Core Technologies

## Languages and Runtimes

- Python 3.11 for the service, CLI, training utilities, and tests.
- TypeScript and React 19 for the browser frontend.
- Node.js 22 is used by CI and the frontend build.

## Frameworks and Libraries

- FastAPI and Uvicorn expose the HTTP service.
- Ultralytics and PyTorch provide Torch inference and training support.
- ONNX Runtime provides the ONNX inference backend.
- Vite, Vitest, ESLint, and TypeScript support the frontend.

## Build, Test, and Development Tools

- Python dependencies are pinned in `requirements.txt` and
  `requirements-dev.txt`.
- Frontend commands are defined in `frontend/package.json`.
- Python tests use `unittest`; CI runs the frontend checks and Python suite.
- Docker builds the frontend and packages the CPU-only service.

## External Services and Infrastructure

- GitHub Actions runs the CI workflow in `.github/workflows/ci.yml`.
- Docker is the documented deployment target.
- Dataset metadata references Roboflow; runtime inference is local.

## Important Technical Constraints

- `DetectionRuntime` owns model loading and reuses adapters per backend and
  checkpoint.
- Runtime model paths are fixed at the project root and are verified against
  `model-manifest.json` at startup.
- Supported backends are `torch` and `onnx`; supported checkpoints are `best`
  and `last`; CPU is the default device.
- The dataset contract in `dataset/data.yaml` defines the class order used by
  training and model validation.
- The API applies upload-size, image-pixel, timeout, and concurrency limits.
