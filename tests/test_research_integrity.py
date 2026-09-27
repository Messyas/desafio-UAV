from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from src.uavids_study.predictive_experiment import (
    normalize_confusion_rows, validate_experiment_inputs,
)
from tools.fetch_dataset import fetch_dataset
from tools.export_mlflow import prepare_export


class ResearchIntegrityTests(unittest.TestCase):
    def test_each_seed_has_its_own_confusion_denominator(self):
        frame = pd.DataFrame({
            "protocol": ["S2"] * 4, "model": ["rf"] * 4,
            "seed": [1, 1, 2, 2], "true_class_id": [0] * 4,
            "rows": [8, 2, 3, 7],
        })
        normalized = normalize_confusion_rows(frame, ["protocol", "model", "seed"])
        self.assertEqual(normalized["true_class_fraction"].tolist(), [0.8, 0.2, 0.3, 0.7])
        sums = normalized.groupby("seed")["true_class_fraction"].sum()
        self.assertTrue((sums == 1).all())

    def test_absent_true_class_has_zero_fractions(self):
        frame = pd.DataFrame({"seed": [1, 1], "true_class_id": [0, 0], "rows": [0, 0]})
        self.assertEqual(
            normalize_confusion_rows(frame, ["seed"])["true_class_fraction"].tolist(),
            [0.0, 0.0],
        )

    def test_resume_rejects_data_changes_even_with_unchanged_identifiers(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data, splits, results = root / "data.csv", root / "splits.csv", root / "results"
            data.write_text("FlowID,value\n1,10\n", encoding="utf-8")
            splits.write_text("flow_id,fold\n1,0\n", encoding="utf-8")
            validate_experiment_inputs(data, splits, results)
            data.write_text("FlowID,value\n1,11\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Cannot resume"):
                validate_experiment_inputs(data, splits, results)

    def test_resume_rejects_changed_partitions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data, splits, results = root / "data.csv", root / "splits.csv", root / "results"
            data.write_text("unchanged data", encoding="utf-8")
            splits.write_text("fold0", encoding="utf-8")
            validate_experiment_inputs(data, splits, results)
            splits.write_text("fold1", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Cannot resume"):
                validate_experiment_inputs(data, splits, results)

    def test_existing_dataset_is_verified_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            dataset = Path(directory) / "data.csv"
            content = b"known raw data"
            dataset.write_bytes(content)
            source = {"bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
            self.assertEqual(fetch_dataset(dataset, source), source["sha256"])
            dataset.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                fetch_dataset(dataset, source)
            self.assertEqual(dataset.read_bytes(), b"changed")

    def test_tracking_rejects_corrupted_predictions_without_mlflow(self):
        root = Path(__file__).resolve().parents[1]
        config = json.loads((root / "configs/predictive_baseline_v1.json").read_text("utf-8"))
        config_hash = hashlib.sha256(
            json.dumps(config, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            result = Path(directory)
            config_path = result / "config.json"
            config_path.write_text(json.dumps(config), encoding="utf-8")
            (result / "experiment_manifest.json").write_text(json.dumps({
                "config_sha256": config_hash, "experiment_id": config["experiment_id"],
                "completed_jobs": 1,
            }), encoding="utf-8")
            records = result / "job_records"
            records.mkdir()
            (result / "prediction.csv").write_text("corrupted", encoding="utf-8")
            (records / "job.json").write_text(json.dumps({
                "status": "complete", "config_sha256": config_hash,
                "prediction_file": "prediction.csv", "prediction_sha256": "incorrect",
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                prepare_export(result, config_path)


if __name__ == "__main__":
    unittest.main()
