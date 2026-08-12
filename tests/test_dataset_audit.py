import unittest

from scripts.audit_dataset import Annotation, audit, expected_yaml_is_present


class DatasetAuditTests(unittest.TestCase):
    def test_overflowing_annotation_is_clamped_inside_image(self) -> None:
        annotation = Annotation(
            class_id=1,
            center_x=0.75,
            center_y=0.8,
            width=0.5,
            height=0.41,
        )

        repaired = annotation.clamped()

        self.assertTrue(repaired.is_valid())
        self.assertEqual(repaired.class_id, annotation.class_id)
        self.assertAlmostEqual(
            repaired.center_x - repaired.width / 2,
            0.5,
        )
        self.assertAlmostEqual(
            repaired.center_y + repaired.height / 2,
            1.0,
        )

    def test_dataset_yaml_uses_three_class_contract(self) -> None:
        self.assertTrue(expected_yaml_is_present())

    def test_checked_in_dataset_passes_audit(self) -> None:
        report = audit()

        self.assertTrue(report["ok"], report["errors"])


if __name__ == "__main__":
    unittest.main()
