# New Dataset Audit and Repair Report

Audited and repaired 2026-08-04. All 1,206 uploaded images were decoded and
visually reviewed with their annotations overlaid. The repaired active dataset
contains 1,179 images after exact-duplicate cleanup.

## Final dataset

| Split | Images | Share | Boxes | Empty | Pipe burst | Accumulation | Water drop |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 939 | 79.64% | 1,221 | 108 | 358 | 426 | 437 |
| valid | 123 | 10.43% | 181 | 17 | 51 | 49 | 81 |
| test | 117 | 9.92% | 129 | 10 | 47 | 38 | 44 |
| total | 1,179 | 100% | 1,531 | 135 | 456 | 513 | 562 |

The dataset audit passes with no malformed records, boundary violations,
missing pairs, orphan labels, unknown classes, or exact duplicate images.
Ultralytics resolves all three split paths and the intended class mapping.

## Repairs made

- Merged the unexpected `leak` class into `pipe burst`. Its 11 annotations on
  nine images described the same active escape-source concept.
- Remapped the export from four class IDs back to the project contract:
  `0 pipe burst`, `1 water accumulation`, `2 water drop`.
- Clipped 31 boxes to the actual image boundary.
- Converted two nine-field polygon records to valid five-field YOLO boxes.
- Cleared five damage-only accumulation annotations showing mold, staining, or
  damaged flooring without visible standing water. The images remain as hard
  negatives.
- Moved 27 exact duplicate image/label pairs into a recoverable backup.
- Reassigned 32 source-related image/label pairs so the confirmed large nozzle
  and dispensing sequences occur in only one split.
- Corrected `dataset/data.yaml` paths and replaced stale exported metadata.
- Made `scripts/audit_dataset.py` report malformed labels as audit errors
  instead of terminating at the first one.

## Recovery

The pre-repair label files and metadata are stored under
`.scratch/dataset-v3-repair-backup-20260804`. Removed duplicate pairs and their
mapping are under its `removed-exact-duplicates` directory.

## Items deliberately left unchanged

- A conservative perceptual-hash screen reports nine small cross-split
  candidate clusters containing 20 images. Several combine unrelated filenames
  and scenes, so they were not moved based on visual similarity alone.
- Forty-two images have a side below 256 pixels. Upscaling cannot restore
  missing detail; replace them only when higher-resolution originals exist.
- Some intentional hose, sprinkler, faucet, rain/dew, and old-damage scenes
  remain policy-dependent. They were not relabeled where intent or visible
  standing water could not be established confidently from the image alone.
- Repeated frames still reduce effective diversity within individual splits.
  Future additions should favor new scenes over adjacent frames from the same
  recording.

## Verdict

The repaired export is structurally ready for a controlled three-class
YOLOv8n training run. Keep this validation and test composition unchanged while
comparing the next run with the previous baseline.

The dataset-specific audit tests pass. The full application suite cannot pass
until the currently registered older `best` checkpoint is replaced: its stored
class list does not match this three-class dataset. Its manifest was not edited,
because metadata cannot make incompatible trained weights compatible. Train the
new checkpoint first, then regenerate and verify the model manifest.
