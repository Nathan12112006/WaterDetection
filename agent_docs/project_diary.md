<!-- codex-workflow-bootstrap-template -->
# Project Diary

Record only durable decisions, discarded approaches, and reusable lessons.

## Decisions and Lessons

- Keep model loading behind `DetectionRuntime` so CLI and API inference share
  model verification, lazy loading, and backend selection behavior.
- Treat the root model files and `model-manifest.json` as one integrity-checked
  runtime set; regenerate the manifest after exporting matching checkpoints.
