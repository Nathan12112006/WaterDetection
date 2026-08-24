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

## Database and App API

Start the Docker MySQL 5.7 service, apply the schema, and start the API:

```powershell
docker compose up -d mysql57
alembic upgrade head
water-workflow-api
```

Open `http://127.0.0.1:8000/docs` for Swagger UI. See
`docs/api-development.md` for the first camera, alarm, and internal detection
event endpoints.
