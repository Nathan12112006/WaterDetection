# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS frontend-build

WORKDIR /frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend ./
RUN npm run build


FROM python:3.11.15-slim-bookworm

# Keep Python output visible in Docker logs and do not create __pycache__ files.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=0 \
    PIP_DEFAULT_TIMEOUT=300 \
    PIP_RETRIES=10 \
    YOLO_CONFIG_DIR=/tmp/ultralytics

WORKDIR /app

# OpenCV needs these small Linux runtime libraries to process images.
RUN apt-get update \
    && apt-get install --yes --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install CPU-only PyTorch first so Ultralytics does not install a CUDA build.
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install torch==2.13.0 torchvision==0.28.0 \
        --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir -r requirements.txt

# Run the service without root privileges.
RUN groupadd --system --gid 10001 yolo \
    && useradd --system --uid 10001 --gid yolo \
        --create-home --home-dir /home/yolo yolo

# Copy only the application code and model files required by the service.
COPY --chown=yolo:yolo api ./api
COPY --chown=yolo:yolo config ./config
COPY --chown=yolo:yolo models ./models
COPY --chown=yolo:yolo service ./service
COPY --chown=yolo:yolo utils ./utils
COPY --from=frontend-build --chown=yolo:yolo /frontend/dist ./frontend/dist
COPY --chown=yolo:yolo best.pt waterAccubest.pt ./

USER yolo:yolo

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"]

CMD ["python", "-m", "uvicorn", "api.app:app", "--host", "0.0.0.0", "--port", "8000"]
