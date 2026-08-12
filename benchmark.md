# Benchmarking the fixed ensemble

Run the benchmark from the repository root:

```powershell
python benchmark.py --image test1.jpg --conf 0.25 --device cpu --warmup 2 --runs 10
```

The command creates one `DetectionRuntime`, which owns the fixed ensemble
(`best.pt` plus `waterAccubest.pt`). Model paths and backend choices are not
caller-configurable.

The report contains cold detection time (including lazy model loading),
average/median/fastest/slowest cached inference time, and the number of
detections returned. The command exits with status `0` when all measurements
complete and `1` if runtime initialization or inference fails.
