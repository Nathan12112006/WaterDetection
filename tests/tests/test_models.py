from __future__ import annotations

import unittest

from water_workflow.config import ModelConfig
from water_workflow.models import create_model
from water_workflow.models.noop import NoOpModel


class ModelFactoryTests(unittest.TestCase):
    def test_noop_backend_can_be_created(self) -> None:
        self.assertIsInstance(create_model(ModelConfig(backend="noop")), NoOpModel)

    def test_unknown_backend_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported model backend"):
            create_model(ModelConfig(backend="unknown"))


if __name__ == "__main__":
    unittest.main()
