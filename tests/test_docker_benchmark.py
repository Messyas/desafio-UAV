import unittest

import numpy as np

from src.uavids_study.docker_benchmark import (
    encode_instances,
    parse_bytes,
    percentile_summary_ns,
)
from src.uavids_study.docker_inference_service import InferenceState


class DockerBenchmarkUtilitiesTest(unittest.TestCase):
    def test_parse_binary_memory_units(self) -> None:
        self.assertEqual(parse_bytes("512MiB"), 512 * 1024**2)
        self.assertEqual(parse_bytes("1.5 GiB"), 1.5 * 1024**3)

    def test_percentiles_convert_nanoseconds_to_microseconds(self) -> None:
        summary = percentile_summary_ns(np.array([1_000, 2_000, 3_000]))
        self.assertEqual(summary["count"], 3)
        self.assertEqual(summary["p50_us"], 2.0)
        self.assertEqual(summary["max_us"], 3.0)

    def test_payload_preserves_two_dimensional_shape(self) -> None:
        payload = encode_instances(np.zeros((1, 18), dtype=np.float64))
        self.assertIn(b'"instances":[[', payload)

    def test_service_rejects_wrong_feature_count(self) -> None:
        state = InferenceState.__new__(InferenceState)
        state.feature_count = 18
        with self.assertRaisesRegex(ValueError, "Expected shape"):
            state.validate_instances({"instances": [[0.0] * 17]})

    def test_service_accepts_valid_finite_matrix(self) -> None:
        state = InferenceState.__new__(InferenceState)
        state.feature_count = 18
        matrix = state.validate_instances({"instances": [[0.0] * 18]})
        self.assertEqual(matrix.shape, (1, 18))
        self.assertEqual(matrix.dtype, np.float64)


if __name__ == "__main__":
    unittest.main()
