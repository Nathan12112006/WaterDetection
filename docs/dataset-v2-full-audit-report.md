# Dataset Version 2 - Final Audit and Repair Report

Audited and repaired 2026-08-03. Every one of the original 1,152 images was
decoded and visually reviewed with its annotations overlaid. The active
dataset now contains 1,125 images after recoverable exact-duplicate cleanup.

## Current status

`python scripts/audit_dataset.py` passes with `ok: true`.

| Split | Images | Share | Boxes | Empty/negative | Pipe burst | Accumulation | Water drop |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 885 | 78.67% | 1,128 | 107 | 334 | 425 | 369 |
| valid | 121 | 10.76% | 178 | 17 | 49 | 49 | 80 |
| test | 119 | 10.58% | 133 | 11 | 47 | 39 | 47 |
| total | 1,125 | 100% | 1,439 | 135 | 430 | 513 | 496 |

There are no missing image/label pairs, orphan labels, malformed records,
out-of-bounds boxes, or exact duplicate image groups.

## Repairs completed

- Corrected 31 boxes that crossed an image boundary.
- Converted two incompatible nine-field polygon records to five-field YOLO
  boxes.
- Moved 27 redundant exact image/label pairs to the recoverable backup at
  `.scratch/dataset-dedup-backup-20260803`.
- Consolidated four visually confirmed capture sequences into one split per
  source, including the large dispensing/nozzle sequences that previously
  crossed train, validation, and test.
- Consolidated seven additional original/derived-image groups whose shared
  source name was unambiguous.
- Cleared five accumulation annotations that showed old staining, mold, or
  damaged flooring but no visible standing water. Their images remain as hard
  negatives.
- Corrected the local paths in `dataset/data.yaml` and replaced stale class
  metadata in `dataset/README.roboflow.txt`.
- Clarified the annotation policy for pendant droplets while excluding generic
  wet films and stains.

## Remaining review signals

The dataset is structurally ready for a controlled training run. These items
were deliberately not changed automatically:

- A conservative perceptual-hash scan still reports nine cross-split candidate
  clusters containing 20 images. They are small and several combine unrelated
  filenames, so similarity alone is not sufficient evidence to move or remove
  them. Review their source provenance in Roboflow if available.
- Thirty-eight images have a side below 256 pixels. Upscaling would not restore
  missing detail; replace them only when a higher-resolution original can be
  obtained.
- A few sprinkler, hose, faucet, natural dew, and rain scenes remain policy
  decisions. They should only be relabeled after deciding whether deployment
  should detect all visible water release or specifically unintended plumbing
  leaks.
- Large same-source sequences still reduce effective diversity even though the
  confirmed sequences no longer leak across splits. Future additions should
  prioritize new locations, lighting, pipe materials, backgrounds, camera
  distances, and very small droplets instead of adjacent video frames.

## Training recommendation

Use this repaired version for the next YOLOv8n baseline and compare per-class
precision, recall, and mAP50-95 with the previous run. Keep the current test set
unchanged for that comparison. For small water drops, train at 960 or 1280
pixels if GPU memory permits and inspect false negatives at native resolution.
More epochs are useful only while validation metrics continue improving; they
cannot compensate for unclear pixels, inconsistent labels, or repeated scenes.
