from __future__ import annotations

import ast
import hashlib
import json
import unittest
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = ROOT / "artifacts" / "models" / "deployment_candidates_v1"
BENCHMARK_DIR = ROOT / "benchmarks" / "local_inference_v1"


class SystemBenchmarkTests(unittest.TestCase):
    def test_frozen_model_hashes_and_schema(self) -> None:
        manifest = json.loads((ARTIFACT_DIR / "manifest.json").read_text("utf-8"))
        schema = json.loads((ARTIFACT_DIR / "schema.json").read_text("utf-8"))
        self.assertFalse(manifest["predictive_metrics_computed_on_training_data"])
        self.assertEqual(schema["input_shape"], [None, 18])
        self.assertEqual(len(schema["class_order"]), 5)
        for model in manifest["models"]:
            path = ARTIFACT_DIR / model["file"]
            observed = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(observed, model["sha256"])

    def test_local_benchmark_is_complete_and_raw_counts_match(self) -> None:
        manifest = json.loads((BENCHMARK_DIR / "manifest.json").read_text("utf-8"))
        self.assertTrue(manifest["complete"])
        self.assertEqual(manifest["completed_models"], 2)
        for model in ("xgboost", "random_forest"):
            individual = pd.read_csv(BENCHMARK_DIR / f"{model}__individual.csv.gz")
            batches = pd.read_csv(BENCHMARK_DIR / f"{model}__batch.csv.gz")
            self.assertEqual(len(individual), 5_000)
            self.assertEqual(len(batches), 600)
            self.assertTrue((individual["duration_ns"] > 0).all())
            self.assertTrue((batches["duration_ns"] > 0).all())

    def test_all_generated_notebooks_parse(self) -> None:
        notebook_dir = ROOT / "notebooks" / "research"
        expected = {
            "00_auditoria_e_protocolo.ipynb",
            "01_baselines_preditivos.ipynb",
            "02_tuning_aninhado_s2.ipynb",
            "03_estabilidade_sementes_s2.ipynb",
            "04_benchmark_local.ipynb",
        }
        self.assertTrue(expected.issubset({path.name for path in notebook_dir.glob("*.ipynb")}))
        for path in notebook_dir.glob("*.ipynb"):
            notebook = json.loads(path.read_text(encoding="utf-8"))
            for cell in notebook["cells"]:
                if cell["cell_type"] == "code":
                    ast.parse("".join(cell["source"]))


if __name__ == "__main__":
    unittest.main()
