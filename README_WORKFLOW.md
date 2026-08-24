# Workflow skeleton

Use `yologpu_env` to run the video workflow. Press `q` in the display window to quit.

## Camera input

```powershell
conda activate yologpu_env
python -m pip install -e .
water-workflow --config configs/default.yaml --source camera --camera-index 0
```

## Local video input

```powershell
conda activate yologpu_env
water-workflow --source file --file "D:\path\to\test.mp4"
```

## YOLO inference

The default configuration loads `model/best.pt` through the `yolo` backend.
Model paths in YAML are resolved relative to the YAML file. Run the default
model with either input type:

```powershell
water-workflow --source camera --camera-index 0
water-workflow --source file --file "D:\path\to\test.mp4"
```

You can still override the configured model from the command line:

```powershell
water-workflow --source file --file "D:\path\to\test.mp4" --model yolo --weights "D:\other\best.pt"
```

The video source knows nothing about YOLO. A future frame-difference model,
segmentation model, tracker, or ensemble can implement the same `predict(frame)`
interface and be selected in `models/factory.py`.

To persist YOLO detections into MySQL, create a camera row through the API,
then set `database.enabled: true` and that row's `database.camera_id` in
`configs/default.yaml`. The workflow registers the model in `model_versions`
once and writes non-empty frames to `detection_events` and `alarms`.

Example development configuration:

```yaml
database:
  enabled: true
  camera_id: 1
  write_detection_events: true

alarm:
  # water drop/滴水 is immediate; other classes need three consecutive frames.
  confirmation_frames: 3
  water_drop_labels: [water drop, water_drop, 滴水, 水滴]
```

Keep `enabled: false` when you only want to preview a video without writing
database records. The writer stores one event per detection box on each
processed frame that contains detections. Alarm state is updated once per
label and frame: `water drop` (and the configured Chinese aliases) becomes
active immediately, while other labels become `candidate` until they are
detected on `alarm.confirmation_frames` consecutive frame indexes. A gap in
frame indexes resets the candidate streak. Automatic recovery and spatial
IoU matching are still separate follow-up work.

## Database and App API

Start the Docker MySQL 5.7 service, apply the schema, and start the API:

```powershell
docker compose up -d mysql57
alembic upgrade head
water-workflow-api
```

Open `http://127.0.0.1:8000/docs` for Swagger UI. See
`docs/api-development.md` for camera, alarm, detection-event, model-version,
and internal ingestion endpoints.
