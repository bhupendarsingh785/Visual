import unittest
from training_runtime import validate_training_limits


class TrainingLimitTests(unittest.TestCase):
    def test_defaults_are_bounded(self):
        limits = validate_training_limits()
        self.assertEqual(limits["epochs"], 3)
        self.assertEqual(limits["max_seconds"], 3600)

    def test_rejects_unbounded_or_invalid_values(self):
        for kwargs in (
            {"epochs": 0},
            {"epochs": 501},
            {"max_steps_per_epoch": 100001},
            {"max_seconds": 86401},
            {"patience": 0},
            {"gradient_clip_norm": float("nan")},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    validate_training_limits(**kwargs)


if __name__ == "__main__":
    unittest.main()
