# Dataset Version 3 Repair Report

Audited and repaired 2026-08-04. All 1,206 uploaded images were decoded and
reviewed on annotated contact sheets.

## Repairs completed

- Merged the unintended `leak` class into `pipe burst` and remapped the export
  to the three-class order: `pipe burst`, `water accumulation`, `water drop`.
- Corrected `dataset/data.yaml` to use the local split paths and three classes.
- Clipped 31 boxes to the image boundary.
- Converted two nine-field polygon records into five-field YOLO boxes.
- Cleared five damage-only accumulation labels that contained mold, staining,
  or damaged flooring but no visible standing water.
- Moved 27 exact duplicate image/label pairs into the recoverable repair
  backup.
- Visually confirmed nine remaining cross-split near-duplicate source groups
  and moved 11 training variants into the backup, retaining their evaluation
  copies.

## Final dataset

| Split | Images | Share | Pipe burst | Accumulation | Water drop |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 928 | 79.45% | 343 | 426 | 435 |
| valid | 123 | 10.53% | 51 | 49 | 81 |
| test | 117 | 10.02% | 47 | 38 | 44 |

The original labels and metadata, exact duplicates, and removed near-duplicate
training variants are recoverable under
`.scratch/dataset-v3-repair-backup-20260804`.

Final verification reports 928 paired train files, 123 paired validation
files, and 117 paired test files; zero malformed or out-of-bounds records;
zero exact duplicate groups; and zero perceptual-hash candidate groups crossing
the split boundaries. Ultralytics resolves all three dataset paths and class
names successfully.

## Intentionally unchanged

- Low-resolution files were not upscaled because interpolation cannot restore
  missing visual detail.
- Ambiguous intentional-flow scenes such as hoses and sprinklers were not
  relabeled without a narrower deployment policy.
- Same-source frames contained entirely within one split remain a diversity
  concern, but they no longer contaminate evaluation through the confirmed
  cross-split groups.
