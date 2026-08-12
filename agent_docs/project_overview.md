<!-- codex-workflow-bootstrap-template -->
# Project Overview

## Purpose

Provide CLI, HTTP API, and browser workflows for detecting visible water leaks
in images and returning detection classes, confidence scores, and bounding
boxes.

## Scope

The project includes FastAPI routes, a React frontend, Torch and ONNX runtime
backends, model training and dataset-audit utilities, tests, and a Docker
deployment definition.

## Architecture

The CLI and FastAPI application both call `service.DetectionRuntime`.
`DetectionRuntime` verifies the fixed model artifacts, lazily creates a Torch
or ONNX adapter for the selected checkpoint, and returns `models.Detection`
values. FastAPI serves the built frontend and exposes detection and health
routes.

## Main Workflows

- Audit the dataset, train checkpoints, export matching ONNX files, and update
  the model manifest.
- Run one image through `main.py` with a selected backend and checkpoint.
- Build the frontend and run FastAPI for browser/API detection.
- Run the frontend checks and Python `unittest` suite.
- Build and run the CPU-only Docker image.

## Major Decisions

- Model loading and model-path ownership are centralized in
  `DetectionRuntime`.
- Torch and ONNX checkpoints are treated as matching runtime artifacts and are
  checked through the model manifest.
- The service defaults to CPU execution and reads server limits from
  environment variables.
