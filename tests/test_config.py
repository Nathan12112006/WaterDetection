from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from water_workflow.config import load_config


class ConfigTests(unittest.TestCase):
    def test_load_config_uses_yaml_values(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "test.yaml"
            config_file.write_text(
                "video:\n  source: file\n  file_path: sample.mp4\nmodel:\n  backend: noop\n",
                encoding="utf-8",
            )

            config = load_config(config_file)

        self.assertEqual(config.video.source, "file")
        self.assertEqual(config.video.file_path, str((config_file.parent / "sample.mp4").resolve()))
        self.assertEqual(config.model.backend, "noop")

    def test_relative_model_path_is_resolved_from_config_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "configs" / "test.yaml"
            config_file.parent.mkdir()
            config_file.write_text("model:\n  backend: yolo\n  weights: ../model/best.pt\n", encoding="utf-8")

            config = load_config(config_file)

        expected = (config_file.parent / "../model/best.pt").resolve()
        self.assertEqual(config.model.weights, str(expected))

    def test_load_config_rejects_unknown_keys(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_file = Path(directory) / "invalid.yaml"
            config_file.write_text("video:\n  unknown_option: true\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unknown_option"):
                load_config(config_file)


if __name__ == "__main__":
    unittest.main()
