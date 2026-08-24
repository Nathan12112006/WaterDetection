# API and database development

## Initialize or upgrade the schema

```powershell
conda activate yologpu_env
cd D:\ProgramProject_Hub\WaterDetection
alembic upgrade head
```

## Start the API

```powershell
water-workflow-api
```

Open `http://127.0.0.1:8000/docs` for Swagger UI.

The first development endpoints are:

- `GET /api/v1/health`
- `POST/GET/PATCH /api/v1/cameras`
- `GET /api/v1/alarms`
- `GET /api/v1/alarms/{id}`
- `POST /api/v1/alarms/{id}/acknowledge`
- `POST /api/v1/alarms/{id}/resolve`
- `POST /api/v1/internal/detection-events`

The internal event endpoint currently creates an alarm immediately and merges
later events with the same camera and label into the active alarm. This is a
development rule only. The final temporal confirmation/state machine will
replace it when its thresholds are validated.
