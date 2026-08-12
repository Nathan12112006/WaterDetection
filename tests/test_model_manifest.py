import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from service.model_manifest import (
    EXPECTED_GENERAL_CLASS_NAMES,
    EXPECTED_SPECIALIST_CLASS_NAMES,
    GENERAL_MODEL_FILENAME,
    RUNTIME_MODEL_FILENAMES,
    SPECIALIST_MODEL_FILENAME,
    normalize_class_names,
    validate_loaded_class_names,
    verify_runtime_models,
)
from utils import ModelManifestError


class RuntimeModelVerificationTests(unittest.TestCase):
    def test_verifies_only_the_two_fixed_torch_files(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / GENERAL_MODEL_FILENAME).write_bytes(b"general")
            (root / SPECIALIST_MODEL_FILENAME).write_bytes(b"specialist")

            paths = verify_runtime_models(root)

        self.assertEqual(
            paths,
            {
                "general": root / GENERAL_MODEL_FILENAME,
                "specialist": root / SPECIALIST_MODEL_FILENAME,
            },
        )
        self.assertEqual(
            RUNTIME_MODEL_FILENAMES,
            {
                "general": "best.pt",
                "specialist": "waterAccubest.pt",
            },
        )

    def test_manifest_is_not_required_for_runtime_verification(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / GENERAL_MODEL_FILENAME).write_bytes(b"general")
            (root / SPECIALIST_MODEL_FILENAME).write_bytes(b"specialist")

            self.assertFalse((root / "model-manifest.json").exists())
            verify_runtime_models(root)

    def test_missing_general_model_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / SPECIALIST_MODEL_FILENAME).write_bytes(b"specialist")

            with self.assertRaisesRegex(ModelManifestError, "best.pt"):
                verify_runtime_models(root)

    def test_missing_specialist_model_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / GENERAL_MODEL_FILENAME).write_bytes(b"general")

            with self.assertRaisesRegex(ModelManifestError, "waterAccubest.pt"):
                verify_runtime_models(root)

    def test_empty_runtime_model_is_rejected(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            (root / GENERAL_MODEL_FILENAME).write_bytes(b"")
            (root / SPECIALIST_MODEL_FILENAME).write_bytes(b"specialist")

            with self.assertRaisesRegex(ModelManifestError, "non-empty"):
                verify_runtime_models(root)


class LoadedClassMapTests(unittest.TestCase):
    def test_normalizes_indexed_dict_and_sequence_maps(self) -> None:
        self.assertEqual(
            normalize_class_names(
                {
                    0: "pipe burst",
                    1: "water accumulation",
                    2: "water drop",
                }
            ),
            EXPECTED_GENERAL_CLASS_NAMES,
        )
        self.assertEqual(
            normalize_class_names(["water damage"]),
            EXPECTED_SPECIALIST_CLASS_NAMES,
        )

    def test_validates_exact_role_class_maps(self) -> None:
        self.assertEqual(
            validate_loaded_class_names(
                "general",
                {
                    "0": "pipe burst",
                    "1": "water accumulation",
                    "2": "water drop",
                },
            ),
            EXPECTED_GENERAL_CLASS_NAMES,
        )
        self.assertEqual(
            validate_loaded_class_names("specialist", {0: "water damage"}),
            EXPECTED_SPECIALIST_CLASS_NAMES,
        )

    def test_wrong_role_classes_are_rejected(self) -> None:
        with self.assertRaisesRegex(ModelManifestError, "must be"):
            validate_loaded_class_names("general", {0: "water damage"})

        with self.assertRaisesRegex(ModelManifestError, "must be"):
            validate_loaded_class_names(
                "specialist",
                {0: "pipe burst", 1: "water accumulation", 2: "water drop"},
            )

    def test_malformed_class_maps_are_rejected(self) -> None:
        malformed_maps = (
            {1: "water damage"},
            {0: ""},
            {0: "water damage", 2: "extra"},
            "water damage",
        )
        for class_map in malformed_maps:
            with self.subTest(class_map=class_map):
                with self.assertRaises(ModelManifestError):
                    normalize_class_names(class_map)


if __name__ == "__main__":
    unittest.main()
