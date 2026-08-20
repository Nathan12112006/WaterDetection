"""Upload the two runtime-owned Torch weights to Roboflow."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from roboflow import Roboflow


PROJECT_ROOT = Path(__file__).resolve().parent
CHECKPOINTS = (
    ("waterAccubest.pt", "WaterAccumulation"),
    ("best.pt", "WaterDetection"),
)


def required_environment_variable(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(
            f"Missing {name}. Add it to {PROJECT_ROOT / '.env'}."
        )
    return value


def main() -> int:
    load_dotenv(PROJECT_ROOT / ".env")

    api_key = required_environment_variable("ROBOFLOW_API_KEY")
    workspace_id = required_environment_variable("ROBOFLOW_WORKSPACE_ID")
    project_id = required_environment_variable("ROBOFLOW_PROJECT_ID")
    model_type = os.getenv("ROBOFLOW_MODEL_TYPE", "yolov8").strip()

    missing_checkpoints = [
        filename
        for filename, _ in CHECKPOINTS
        if not (PROJECT_ROOT / filename).is_file()
    ]
    if missing_checkpoints:
        raise SystemExit(
            "Missing checkpoint files: " + ", ".join(missing_checkpoints)
        )

    roboflow = Roboflow(api_key=api_key)
    workspace = roboflow.workspace(workspace_id)

    for filename, default_model_name in CHECKPOINTS:
        environment_name = (
            "ROBOFLOW_"
            + Path(filename).stem.upper()
            + "_MODEL_NAME"
        )
        model_name = os.getenv(
            environment_name,
            default_model_name,
        ).strip()

        print(f"Uploading {filename} as {model_name}...")
        workspace.deploy_model(
            model_type=model_type,
            model_path=str(PROJECT_ROOT),
            filename=filename,
            project_ids=[project_id],
            model_name=model_name,
        )
        print(f"Uploaded {filename} successfully.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
