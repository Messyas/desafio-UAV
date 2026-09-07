from __future__ import annotations

import json
import ast
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.uavids_study.predictive_experiment import (
    build_estimator,
    file_hash,
    predictive_metrics,
    write_gzip_csv,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "configs" / "predictive_baseline_v1.json"
RESULT_DIR = PROJECT_ROOT / "results" / "predictive_baseline_v1"


class PredictiveExperimentTests(unittest.TestCase):
    def test_primary_features_exclude_identifiers(self) -> None:
        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        prohibited = {"FlowID", "SrcAddr", "DstAddr", "Protocol", "label"}
        self.assertTrue(prohibited.isdisjoint(config["primary_features"]))
        self.assertTrue(config["models"]["random_forest_with_flow_id"]["diagnostic_only"])

    def test_scaler_learns_only_from_training_values(self) -> None:
        model_config = {
            "scale": True,
            "parameters": {"C": 1.0, "max_iter": 100, "solver": "lbfgs"},
        }
        pipeline = build_estimator(
            "logistic_regression", model_config, seed=7, threads=1
        )
        x_train = pd.DataFrame({"feature": [0.0, 1.0, 2.0, 3.0]})
        y_train = np.array([0, 0, 1, 1])
        x_test = pd.DataFrame({"feature": [1_000_000.0]})
        pipeline.fit(x_train, y_train)
        pipeline.predict(x_test)
        self.assertAlmostEqual(float(pipeline.named_steps["scaler"].mean_[0]), 1.5)

    def test_metrics_use_fixed_class_order_and_zero_for_absent_predictions(self) -> None:
        y_true = np.array([0, 0, 1, 1, 2, 2])
        y_pred = np.array([0, 0, 0, 0, 0, 0])
        probabilities = np.array(
            [[0.8, 0.1, 0.1]] * len(y_true), dtype=np.float64
        )
        metrics, class_rows, confusion_rows = predictive_metrics(
            y_true, y_pred, probabilities, ["normal", "attack_a", "attack_b"]
        )
        self.assertAlmostEqual(metrics["accuracy"], 1 / 3)
        self.assertEqual(class_rows[1]["f1"], 0.0)
        self.assertEqual(class_rows[2]["f1"], 0.0)
        self.assertEqual(sum(row["rows"] for row in confusion_rows), len(y_true))

    def test_gzip_prediction_output_is_deterministic(self) -> None:
        frame = pd.DataFrame({"row_id": [0, 1], "prediction": ["a", "b"]})
        with tempfile.TemporaryDirectory() as directory:
            first = Path(directory) / "first.csv.gz"
            second = Path(directory) / "second.csv.gz"
            write_gzip_csv(first, frame)
            write_gzip_csv(second, frame)
            self.assertEqual(file_hash(first), file_hash(second))

    def test_full_experiment_manifest_is_complete(self) -> None:
        manifest = json.loads(
            (RESULT_DIR / "experiment_manifest.json").read_text(encoding="utf-8")
        )
        self.assertTrue(manifest["complete"])
        self.assertEqual(manifest["completed_jobs"], 105)
        self.assertEqual(manifest["completed_jobs"], manifest["expected_jobs"])

    def test_saved_oof_predictions_reproduce_random_forest_s0_metric(self) -> None:
        paths = sorted(
            (RESULT_DIR / "job_predictions").glob(
                "s0__fold_*__random_forest__seed_*.csv.gz"
            )
        )
        self.assertEqual(len(paths), 5)
        predictions = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
        self.assertEqual(len(predictions), 122_171)
        self.assertTrue(predictions["row_id"].is_unique)

        config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        class_to_id = {
            name: class_id for class_id, name in enumerate(config["class_order"])
        }
        y_true = predictions["y_true"].map(class_to_id).to_numpy(dtype=np.int8)
        y_pred = predictions["y_pred"].map(class_to_id).to_numpy(dtype=np.int8)
        probability_columns = [
            f"probability__{name.lower().replace(' ', '_')}"
            for name in config["class_order"]
        ]
        probabilities = predictions[probability_columns].to_numpy(dtype=np.float64)
        probabilities /= probabilities.sum(axis=1, keepdims=True)
        metrics, _, _ = predictive_metrics(
            y_true, y_pred, probabilities, config["class_order"]
        )
        pooled = pd.read_csv(RESULT_DIR / "metrics_pooled_oof.csv")
        expected = pooled.query(
            "protocol == 'S0' and model == 'random_forest'"
        )["f1_macro"].iloc[0]
        self.assertAlmostEqual(metrics["f1_macro"], expected, places=12)

    def test_predictive_notebook_code_cells_parse(self) -> None:
        path = PROJECT_ROOT / "notebooks" / "research" / "01_baselines_preditivos.ipynb"
        notebook = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(notebook["nbformat"], 4)
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                ast.parse("".join(cell["source"]))


if __name__ == "__main__":
    unittest.main()
