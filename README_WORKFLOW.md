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

The default backend is `noop`, which tests only the video/display path. To use
the existing model:

```powershell
water-workflow --source file --file "D:\path\to\test.mp4" --model yolo --weights "D:\path\to\best.pt"
```

The video source knows nothing about YOLO. A future frame-difference model,
segmentation model, tracker, or ensemble can implement the same `predict(frame)`
interface and be selected in `models/factory.py`.
