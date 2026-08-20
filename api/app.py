"""Expose YOLO object detection through a FastAPI application."""

import asyncio
import io
import os
from collections.abc import AsyncIterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from functools import partial
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile, status
from PIL import Image, ImageDraw, UnidentifiedImageError
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse, Response

from api.schemas import DetectionResponse
from config import ServiceConfig
from config.settings import ModelSelection
from models import Detection
from service import DetectionRuntime
from utils import DetectionError, configure_logging

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_FRONTEND_DIST = _PROJECT_ROOT / "frontend" / "dist"
_UI_PATH = _FRONTEND_DIST / "index.html"
_NO_CACHE_HEADERS = {"Cache-Control": "no-store, max-age=0"}
_CLASS_COLORS = {
    "pipe burst": "#fb7185",
    "water accumulation": "#facc15",
    "water drop": "#38bdf8",
    "water damage": "#facc15",
}
# Retain the module-level alias for callers that import it from this module.
ApiModelSelection = ModelSelection


async def _enforce_upload_limit(file: UploadFile, limit: int) -> None:
    upload_size = file.size
    if upload_size is None:
        original_position = file.file.tell()
        file.file.seek(0, os.SEEK_END)
        upload_size = file.file.tell()
        file.file.seek(original_position)
    if upload_size <= limit:
        return

    await file.close()
    raise HTTPException(
        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
        detail=f"Uploaded file is too large. The limit is {limit} bytes.",
    )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Create the verified fixed-model runtime for the server lifetime."""

    configure_logging()
    service_config = ServiceConfig.from_environment()
    app.state.service_config = service_config
    app.state.detection_runtime = DetectionRuntime(device=service_config.device)
    app.state.inference_slots = asyncio.BoundedSemaphore(
        service_config.max_concurrent_detections
    )
    app.state.inference_executor = ThreadPoolExecutor(
        max_workers=service_config.max_concurrent_detections,
        thread_name_prefix="yolo-inference",
    )
    try:
        yield
    finally:
        executor: ThreadPoolExecutor = app.state.inference_executor
        await asyncio.to_thread(
            executor.shutdown,
            wait=True,
            cancel_futures=True,
        )
        del app.state.inference_executor
        del app.state.inference_slots
        del app.state.detection_runtime
        del app.state.service_config


app = FastAPI(
    title="YOLO Detection Service",
    description="Upload an image and receive YOLO object detections as JSON.",
    version="1.0.0",
    lifespan=lifespan,
)
app.mount(
    "/assets",
    StaticFiles(directory=_FRONTEND_DIST / "assets", check_dir=False),
    name="frontend-assets",
)


@app.get("/health", tags=["service"])
def health() -> dict[str, str]:
    """Report readiness after startup model verification has succeeded."""

    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def detection_ui() -> FileResponse:
    """Serve the browser interface for image detection."""

    return FileResponse(
        _UI_PATH,
        headers=_NO_CACHE_HEADERS,
    )


@app.post(
    "/detect",
    response_model=list[DetectionResponse],
    summary="Detect objects in an uploaded image",
)
async def detect_image(
    request: Request,
    file: Annotated[UploadFile, File(description="Image to process")],
    model: Annotated[
        ApiModelSelection,
        Form(description="Model to run"),
    ] = "water_detection",
    confidence: Annotated[
        float,
        Form(
            ge=0.0,
            le=1.0,
            description="Minimum confidence for returned detections",
        ),
    ] = 0.25,
    confidence_pipe_burst: Annotated[float | None, Form(ge=0.0, le=1.0)] = None,
    confidence_water_accumulation: Annotated[float | None, Form(ge=0.0, le=1.0)] = None,
    confidence_water_drop: Annotated[float | None, Form(ge=0.0, le=1.0)] = None,
) -> list[DetectionResponse]:
    """Detect objects in an uploaded image with the fixed ensemble runtime."""

    service_config: ServiceConfig = request.app.state.service_config
    if file.content_type is None or not file.content_type.startswith("image/"):
        await file.close()
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Uploaded file must be an image.",
        )

    await _enforce_upload_limit(file, service_config.max_upload_bytes)

    image: Image.Image | None = None
    try:
        try:
            with Image.open(file.file) as uploaded_image:
                width, height = uploaded_image.size
                if width * height > service_config.max_image_pixels:
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail=(
                            "Uploaded image has too many pixels. "
                            f"The limit is {service_config.max_image_pixels}."
                        ),
                    )
                image = uploaded_image.convert("RGB")
        except HTTPException:
            raise
        except (
            Image.DecompressionBombError,
            UnidentifiedImageError,
            OSError,
        ) as error:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is not a valid image.",
            ) from error

        runtime: DetectionRuntime = request.app.state.detection_runtime
        inference_slots: asyncio.BoundedSemaphore = (
            request.app.state.inference_slots
        )
        try:
            await asyncio.wait_for(inference_slots.acquire(), timeout=0.05)
        except TimeoutError as error:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=(
                    "The service is processing the maximum number "
                    "of detections."
                ),
            ) from error

        executor: ThreadPoolExecutor = request.app.state.inference_executor
        loop = asyncio.get_running_loop()
        worker_image = image
        try:
            inference_future = loop.run_in_executor(
                executor,
                partial(
                    _detect_and_close_image,
                    runtime,
                    worker_image,
                    model=model,
                    confidence=confidence,
                    class_confidences=_class_confidences(
                        confidence_pipe_burst,
                        confidence_water_accumulation,
                        confidence_water_drop,
                    ),
                ),
            )
            image = None
            inference_future.add_done_callback(
                lambda _completed: inference_slots.release()
            )
        except Exception:
            inference_slots.release()
            raise

        try:
            detections = await asyncio.wait_for(
                asyncio.shield(inference_future),
                timeout=service_config.request_timeout_seconds,
            )
        except TimeoutError as error:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=(
                    "Detection timed out after "
                    f"{service_config.request_timeout_seconds:g} seconds."
                ),
            ) from error
        except DetectionError as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=str(error),
            ) from error

        return [
            DetectionResponse.model_validate(detection.to_dict())
            for detection in detections
        ]
    finally:
        if image is not None:
            image.close()
        await file.close()


@app.post(
    "/detect/annotated",
    response_class=Response,
    responses={
        200: {
            "content": {"image/png": {}},
            "description": "The uploaded image with detection annotations.",
        }
    },
    summary="Detect objects and return an annotated image",
)
async def detect_annotated_image(
    request: Request,
    file: Annotated[UploadFile, File(description="Image to annotate")],
    model: Annotated[
        ApiModelSelection,
        Form(description="Model to run"),
    ] = "water_detection",
    confidence: Annotated[
        float,
        Form(
            ge=0.0,
            le=1.0,
            description="Minimum confidence for drawn detections",
        ),
    ] = 0.25,
    confidence_pipe_burst: Annotated[float | None, Form(ge=0.0, le=1.0)] = None,
    confidence_water_accumulation: Annotated[float | None, Form(ge=0.0, le=1.0)] = None,
    confidence_water_drop: Annotated[float | None, Form(ge=0.0, le=1.0)] = None,
) -> Response:
    """Return a full-resolution PNG with boxes and labels drawn on it."""

    service_config: ServiceConfig = request.app.state.service_config
    await _enforce_upload_limit(file, service_config.max_upload_bytes)

    await file.seek(0)
    source_image = await file.read()
    await file.seek(0)
    detections = await detect_image(
        request,
        file,
        model,
        confidence,
        confidence_pipe_burst,
        confidence_water_accumulation,
        confidence_water_drop,
    )

    with Image.open(io.BytesIO(source_image)) as uploaded_image:
        annotated = uploaded_image.convert("RGB")
    try:
        _draw_annotations(
            annotated,
            [
                Detection(
                    class_name=detection.class_name,
                    confidence=detection.confidence,
                    bbox=detection.bbox,
                )
                for detection in detections
            ],
        )
        output = io.BytesIO()
        annotated.save(output, format="PNG")
    finally:
        annotated.close()

    return Response(
        content=output.getvalue(),
        media_type="image/png",
        headers={
            "Content-Disposition": 'attachment; filename="annotated.png"',
            "Cache-Control": "no-store",
        },
    )


def _draw_annotations(image: Image.Image, detections: list[Detection]) -> None:
    """Draw readable, bounds-safe detection boxes and labels in place."""

    draw = ImageDraw.Draw(image)
    width, height = image.size
    line_width = max(2, round(max(width, height) / 400))
    padding = max(3, line_width)

    for detection in detections:
        raw_x1, raw_y1, raw_x2, raw_y2 = detection.bbox
        x1 = min(max(round(raw_x1), 0), width - 1)
        y1 = min(max(round(raw_y1), 0), height - 1)
        x2 = min(max(round(raw_x2), x1), width - 1)
        y2 = min(max(round(raw_y2), y1), height - 1)
        color = _CLASS_COLORS.get(
            detection.class_name.strip().lower(),
            "#a78bfa",
        )
        draw.rectangle(
            (x1, y1, x2, y2),
            outline=color,
            width=line_width,
        )

        class_label = (
            "water leaking"
            if detection.class_name.strip().lower() == "water damage"
            else detection.class_name
        )
        label = f"{class_label} {detection.confidence:.0%}"
        left, top, right, bottom = draw.textbbox((0, 0), label)
        label_width = right - left + padding * 2
        label_height = bottom - top + padding * 2
        label_y = max(0, y1 - label_height)
        label_x2 = min(width - 1, x1 + label_width)
        draw.rectangle(
            (x1, label_y, label_x2, label_y + label_height),
            fill=color,
        )
        draw.text(
            (x1 + padding, label_y + padding - top),
            label,
            fill="#07111c",
        )


def _detect_and_close_image(
    runtime: DetectionRuntime,
    image: Image.Image,
    *,
    model: ApiModelSelection,
    confidence: float,
    class_confidences: dict[str, float] | None = None,
) -> list[Detection]:
    """Run one bounded ensemble inference while retaining image ownership."""

    try:
        inference_options: dict[str, object] = {"confidence": confidence}
        if model != "water_detection":
            inference_options["model"] = model
        if model != "water_accumulation" and class_confidences is not None:
            inference_options["class_confidences"] = class_confidences
        return runtime.detect(image, **inference_options)
    finally:
        image.close()


def _class_confidences(
    pipe_burst: float | None,
    water_accumulation: float | None,
    water_drop: float | None,
) -> dict[str, float] | None:
    values = {
        "pipe burst": pipe_burst,
        "water accumulation": water_accumulation,
        "water drop": water_drop,
    }
    if any(value is None for value in values.values()):
        return None
    return {name: float(value) for name, value in values.items() if value is not None}
