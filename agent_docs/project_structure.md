<!-- codex-workflow-bootstrap-template -->
# Project Structure

## Directory Layout

- `api/`: FastAPI application and response schemas.
- `config/`: CLI and server configuration.
- `models/`: detection result model.
- `service/`: runtime, model-manifest checks, and backend adapters.
- `utils/`: logging and application exceptions.
- `frontend/`: React/Vite application and frontend tests.
- `tests/`: Python, API, browser-harness, and UI tests.
- `scripts/`: dataset and model-manifest utilities.
- `dataset/`: dataset configuration and splits.
- `runs/`, root checkpoint files, and `model-manifest.json`: training output
  and runtime model artifacts.

## Modules and Responsibilities

- `service/detection_runtime.py` is the shared inference entry point.
- `service/backends/` adapts Torch and ONNX model execution.
- `api/app.py` owns HTTP lifecycle, upload validation, concurrency, and
  response rendering.
- `main.py` and `cli.py` provide the command-line entry point and arguments.
- `frontend/src/` provides the browser user interface and typed client
  modules.

## Main Interfaces and Integration Boundaries

- CLI/API callers select a backend, checkpoint, confidence threshold, and
  image; `DetectionRuntime` normalizes the image and returns detections.
- FastAPI serves the built frontend from `frontend/dist` and exposes `/health`,
  `/detect`, and `/detect/annotated`.
- The model manifest boundary verifies model identities before inference.
- CI integrates Node frontend checks with the Python test suite.

## Tests and Supporting Assets

- Python tests are under `tests/` and run with `python -m unittest`.
- Frontend linting, type checking, tests, and builds run from `frontend/`.
- `test1.jpg` is the documented sample image. The README and Dockerfile define
  root-level `best.pt`, `last.pt`, `best.onnx`, and `last.onnx` as the runtime
  checkpoint set.
