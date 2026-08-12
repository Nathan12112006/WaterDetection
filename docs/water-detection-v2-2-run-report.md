# `water-detection-v2-2` Training Report

Run analyzed: `runs/detect/runs/water-detection-v2-2`  
Model: pretrained YOLOv8n object detector  
Classes: `pipe burst`, `water accumulation`, `water drop`  
Training: 50 epochs, 960-pixel input, batch 8, CPU

## Executive summary

The model learned all three classes, but it is not ready for dependable deployment. Its best validation result was **mAP50 38.7%** and **mAP50-95 18.1%** at epoch 40. Water accumulation is substantially stronger than the other classes. Pipe burst is the weakest class, and water drop remains difficult because many drops are tiny.

The main limitation is now the dataset and validation design, not a lack of epochs. Training losses continued falling, but validation losses mostly flattened after roughly epoch 25. The best checkpoint occurred at epoch 40 and performance declined slightly by epoch 50.

## Run configuration

| Setting | Value |
| --- | ---: |
| Base model | `yolov8n.pt` |
| Epochs | 50 |
| Image size | 960 |
| Batch | 8 |
| Device | CPU |
| Early-stopping patience | 20 |
| Scale augmentation | 0.2 |
| Mosaic | 0.25 |
| Mosaic disabled for final | 20 epochs |
| Runtime | about 6 hours 5 minutes |

## Best and final results

Ultralytics selects `best.pt` using a fitness score dominated by mAP50-95. For this run, the best checkpoint was epoch 40.

| Checkpoint | Precision | Recall | mAP50 | mAP50-95 |
| --- | ---: | ---: | ---: | ---: |
| Best, epoch 40 | 45.8% | 40.7% | 38.7% | 18.1% |
| Final, epoch 50 | 39.7% | 44.5% | 36.6% | 17.3% |

The final epoch traded precision for recall but was worse on both mAP measures. Use `weights/best.pt`, not `weights/last.pt`.

The run's best overall F1 score was approximately **0.43 at confidence 0.186**. This is a useful starting point for testing, not a universal production threshold. Lower confidence increases recall and false alarms; higher confidence improves precision but misses more leaks.

## Performance by class

| Class | AP50 | Assessment |
| --- | ---: | --- |
| Water accumulation | 57.8% | Best class; useful signal, but box consistency needs improvement |
| Water drop | 34.3% | Weak; many small objects are missed and background confusion remains |
| Pipe burst | 23.9% | Weakest class; poor precision-recall tradeoff and many background false positives |

The confusion matrix shows little direct confusion between the three named classes. Most errors are objects missed as background or background regions incorrectly detected as leaks. That means the priority is not merely teaching the model to distinguish the three names; it is teaching what counts as an object and what must remain background.

### Pipe burst

Pipe burst has the lowest AP50. Its precision curve is also the weakest at low and medium confidence. The validation predictions show detections focused on small pipe openings, but the dataset contains large visual variation: strong jets, sprays, damaged joints, outdoor pipes, and indoor scenes. Steam, mist, glare, wet pipe surfaces, hoses, faucets, and ordinary pipe fittings are likely hard negatives.

Use a strict definition: label a pipe burst only when pressurized liquid visibly escapes from a pipe, fitting, crack, or rupture. Do not label steam or mist alone as pipe burst.

### Water accumulation

Water accumulation performs best, but the validation examples show inconsistent spatial definitions. Some boxes tightly cover a puddle while others cover most of a wall, floor, or room. Predictions sometimes create several overlapping boxes on one continuous accumulation region. This inconsistency is a likely reason mAP50-95 remains low even though AP50 is comparatively good.

Choose one rule and apply it everywhere: one box per visually continuous accumulation region, enclosing the visible water rather than the surrounding wall or entire scene.

### Water drop

Water drop is the middle class by AP50, but many examples are extremely small. The current dataset audit found that roughly 43% of training drop boxes have a side below 16 pixels when scaled to 640, and roughly 90% have a side below 32 pixels. At that scale, annotation differences of only a few pixels strongly affect mAP50-95.

Label individually visible, separated drops separately. Use a group box only for a coherent spray or cluster where individual drops cannot be annotated consistently. Pendant drops forming on the underside of a pipe may count as water drop if that rule is applied consistently. Steam or featureless mist should not.

## Training behavior

- Training box, classification, and distribution focal losses fell steadily through epoch 50.
- Validation losses improved rapidly early in training, then flattened and fluctuated after approximately epochs 20-30.
- mAP50 and mAP50-95 continued making small, noisy gains, with the best checkpoint at epoch 40.
- There is a growing train-validation gap. This indicates limited generalization, label inconsistency, or split problems rather than undertraining alone.

### Would more epochs help?

Probably only a little with the current dataset. From epoch 40 to epoch 50, mAP50 fell from 38.7% to 36.6%, and mAP50-95 fell from 18.1% to 17.3%. Extending this exact run is unlikely to create a major improvement. A longer run may find another small peak, but it will not fix mislabeled boxes, repeated validation sources, missing negatives, or weak class coverage.

After cleaning the dataset, train for 80-100 epochs with patience 15-20 and keep `best.pt`. At the current CPU speed, every additional 10 epochs costs roughly another 73 minutes.

## Reliability problems affecting these metrics

The checked-in dataset audit found the following issues:

- 54 images contain 63 invalid or incompatible annotation lines.
- 26 annotations use polygon-style fields in a bounding-box dataset.
- 37 boxes extend outside normalized image boundaries.
- 28 exact duplicate image pairs exist.
- One exact duplicate crosses from training into validation.
- Validation and test each contain 10 repeated-source groups.
- The validation montage visibly repeats several source images with augmented variants.
- 38 images have a side below 256 pixels.

These problems can both hurt training and inflate validation scores. Repeated versions of one source image do not provide independent evidence. The current result should therefore be treated as an iteration metric, not a trustworthy production estimate.

See [dataset-image-fix-report.md](dataset-image-fix-report.md) for the affected file list.

## Recommended improvement plan

### 1. Repair annotations before another full run

Fix every item in the mandatory annotation section of the dataset report. Then run:

    python scripts/audit_dataset.py

Do not launch the next final training run until the structural audit completes without errors.

### 2. Rebuild splits by original source

Keep every crop, frame, download variant, and augmentation derived from the same original image in one split. Remove exact cross-split duplicates. Build a clean validation and test set from independent source scenes. This is essential for honest metrics.

### 3. Standardize class definitions and boxes

- `pipe burst`: box the visible escape source and coherent pressurized jet/spray; exclude steam-only scenes.
- `water accumulation`: one tight box around each continuous visible pool or accumulation region.
- `water drop`: separate boxes for clearly separated drops; one group box only for an inseparable coherent cluster.
- Annotate all qualifying instances in every image. Partially labeled images teach the model that unmarked leaks are background.

### 4. Add targeted data rather than random volume

Prioritize new, independent source images for pipe burst and water drop. Include varied pipe materials, fittings, camera distances, indoor/outdoor lighting, backgrounds, burst directions, droplet sizes, and motion blur.

Add hard-negative images containing:

- intact wet and dry pipes;
- steam, mist, smoke, condensation, and glare without an active leak;
- faucets, hoses, valves, sprinklers, rain, and water reflections;
- stained walls and floors without standing water.

Review false positives from real deployment footage and add those scenes as labeled positives or empty negatives.

### 5. Improve small-object training carefully

Keep 960-pixel training for now. Avoid aggressive crops or scale augmentation that makes tiny drops disappear. After cleaning labels, compare one controlled run at 960 against 1280 only if deployment hardware can afford the latency. For dense tiny droplets, tiled inference may help more than simply adding epochs.

### 6. Compare models only after the data is fixed

YOLOv8n is small and fast. After establishing a clean baseline, compare `yolov8s.pt` at the same image size and dataset version. A larger model may improve localization and subtle features, but it cannot compensate for inconsistent annotations or split leakage.

### 7. Tune confidence on a clean validation set

Start testing around confidence 0.18-0.25. Select the threshold based on the real cost of missed leaks versus false alarms. If missing a burst is much worse than a false alert, prefer a lower threshold and add a temporal rule for video, such as requiring detections in several consecutive frames.

## Success criteria for the next run

Compare the next run against this fixed baseline:

- Overall mAP50: 38.7%
- Overall mAP50-95: 18.1%
- Overall recall: 40.7%
- Pipe-burst AP50: 23.9%
- Water-accumulation AP50: 57.8%
- Water-drop AP50: 34.3%

Require improvement on an independent, source-separated validation set. A lower score immediately after removing leakage may be more honest and more useful than a higher contaminated score.

## Source artifacts

- `runs/detect/runs/water-detection-v2-2/results.csv`
- `runs/detect/runs/water-detection-v2-2/results.png`
- `runs/detect/runs/water-detection-v2-2/BoxPR_curve.png`
- `runs/detect/runs/water-detection-v2-2/BoxF1_curve.png`
- `runs/detect/runs/water-detection-v2-2/confusion_matrix_normalized.png`
- `runs/detect/runs/water-detection-v2-2/val_batch*_labels.jpg`
- `runs/detect/runs/water-detection-v2-2/val_batch*_pred.jpg`
