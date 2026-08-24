# API and database development

## Initialize or upgrade the schema

```powershell
conda activate yologpu_env
cd D:\ProgramProject_Hub\WaterDetection
alembic upgrade head
```

## Start the API

```powershell
# Optional: use a non-default policy/configuration file.
$env:WATER_WORKFLOW_CONFIG = "configs/default.yaml"
water-workflow-api
```

Open `http://127.0.0.1:8000/docs` for Swagger UI.

The first development endpoints are:

- `GET /api/v1/health`
- `POST/GET/PATCH /api/v1/cameras`
- `GET /api/v1/cameras/{id}/status`
- `GET /api/v1/alarms`
- `GET /api/v1/alarms/{id}`
- `POST /api/v1/alarms/{id}/acknowledge`
- `POST /api/v1/alarms/{id}/resolve`
- `GET /api/v1/detection-events`
- `GET /api/v1/model-versions`
- `POST /api/v1/internal/detection-events`

The API reads the alarm policy from `WATER_WORKFLOW_CONFIG` when that
environment variable is set. If it is not set, it uses
`configs/default.yaml` when started from the project directory and otherwise
falls back to the built-in defaults (one frame for water drops, three for
other labels).

## Alarm confirmation policy

The internal event endpoint writes every detection box to
`detection_events`. It updates an alarm once per label and frame:

- `water drop`, `water_drop`, `滴水`, and `水滴` are immediately `active`;
- all other labels require three consecutive frame indexes by default;
- a non-consecutive frame resets a `candidate` alarm's confirmation streak;
- the threshold can be changed in `configs/default.yaml` with
  `alarm.confirmation_frames` and `alarm.water_drop_labels`.

The response may include a `candidate` alarm ID before the threshold is met.
App clients should normally display only `active` and `acknowledged` alarms as
push notifications, while optionally showing candidates in a diagnostic view.

Example queries:

```text
GET /api/v1/alarms?status=active&camera_id=1
GET /api/v1/detection-events?camera_id=1&label=pipe%20burst&page=1&page_size=50
GET /api/v1/cameras/1/status
GET /api/v1/model-versions
```

The current version does not yet implement automatic recovery after a period
without detections, spatial IoU matching for multiple leak locations, or
alarm screenshots/video clips. Those are planned follow-up items.
