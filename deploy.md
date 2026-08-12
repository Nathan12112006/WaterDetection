# CPU Docker Deployment

Docker builds the React frontend in a disposable Node stage, then packages its
static output with FastAPI, the two fixed model files, and the Python
dependencies. The final Linux CPU image runs as the unprivileged UID/GID
`10001` and contains neither Node nor other developer tools.

## Build

Run this command from the repository root while Docker Desktop is using Linux
containers:

```powershell
docker build -t water-leak-service .
```

## Start

For local development:

```powershell
docker run --rm -p 8000:8000 -e YOLO_DEVICE=cpu water-leak-service
```

For a hardened deployment:

```powershell
docker run --rm --init --read-only `
  --tmpfs /tmp:rw,noexec,nosuid,size=64m `
  --cap-drop ALL `
  --security-opt no-new-privileges:true `
  --memory 4g --cpus 2 `
  -p 8000:8000 `
  -e YOLO_DEVICE=cpu `
  water-leak-service
```

The read-only root filesystem prevents runtime modification of application and
model files. `/tmp` remains writable for Ultralytics configuration and other
temporary runtime data. Capabilities and privilege escalation are disabled;
memory and CPU limits prevent one container from exhausting its host. Adjust
the resource limits if real inference measurements show the service needs
more.

At startup, FastAPI verifies and loads the two fixed Torch model files. Each
request selects `water_accumulation` or `water_detection`.

## Smoke verification

Open <http://127.0.0.1:8000/docs> and submit one image to `/detect`. The
request requires an image and optionally accepts `confidence`; backend,
checkpoint, and model-path fields are not exposed. You can also verify that
the service started successfully with:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
docker inspect --format "{{json .State.Health}}" $(docker ps --filter ancestor=water-leak-service --quiet)
```

The health response is `{"status":"ok"}` and Docker should report `healthy`.
Stop the foreground container with `Ctrl+C`. Because `--rm` is used, Docker
removes the stopped container automatically.

## Updating models

Replace `best.pt` and/or `waterAccubest.pt` together with the application
image, then rebuild and restart the container. The runtime owns these fixed
paths; callers cannot select alternate checkpoints.
