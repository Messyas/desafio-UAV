from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

from src.uavids_study.nested_tuning import make_inner_splits, select_candidate


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = PROJECT_ROOT / "results" / "nested_tuning_v2"


class NestedTuningTests(unittest.TestCase):
    def test_s2_inner_splits_keep_groups_separate_and_use_relative_positions(self) -> None:
        groups = np.repeat(np.arange(30), 4)
        labels = np.tile(np.arange(5), 24)
        splits = pd.DataFrame(
            {
                "s2_group": groups,
                "s1_group": np.arange(len(groups)),
            }
        )
        outer_train_rows = np.arange(10, 110)
        folds = make_inner_splits(
            splits,
            labels,
            outer_train_rows,
            "S2",
            n_splits=3,
            seed=17,
        )
        self.assertEqual(len(folds), 3)
        for train_positions, validation_positions in folds:
            self.assertLess(train_positions.max(), len(outer_train_rows))
            self.assertLess(validation_positions.max(), len(outer_train_rows))
            train_groups = set(groups[outer_train_rows[train_positions]])
            validation_groups = set(groups[outer_train_rows[validation_positions]])
            self.assertTrue(train_groups.isdisjoint(validation_groups))

    def test_tie_rule_prefers_lower_registered_complexity(self) -> None:
        candidates = [
            {
                "candidate_id": "large",
                "complexity_rank": 3,
                "mean_inner_f1_macro": 0.95005,
            },
            {
                "candidate_id": "small",
                "complexity_rank": 1,
                "mean_inner_f1_macro": 0.95,
            },
        ]
        selected = select_candidate(candidates, tie_tolerance=0.0001)
        self.assertEqual(selected["candidate_id"], "small")

    def test_nested_experiment_is_complete_and_records_all_fits(self) -> None:
        manifest = json.loads(
            (RESULT_DIR / "experiment_manifest.json").read_text(encoding="utf-8")
        )
        self.assertTrue(manifest["complete"])
        self.assertEqual(manifest["completed_jobs"], 10)
        records = []
        for path in (RESULT_DIR / "job_records").glob("*.json"):
            record = json.loads(path.read_text(encoding="utf-8"))
            if record.get("status") == "complete":
                records.append(record)
                self.assertEqual(record["tuning_fit_count"], 9)
                self.assertEqual(record["total_fit_count"], 10)
                self.assertEqual(len(record["candidate_results"]), 3)
                self.assertEqual(len(record["warnings"]), 0)
        self.assertEqual(len(records), 10)

    def test_nested_oof_predictions_cover_each_row_once_per_model(self) -> None:
        for model in ("random_forest", "xgboost"):
            paths = sorted(
                (RESULT_DIR / "job_predictions").glob(f"s2__fold_*__{model}__*.csv.gz")
            )
            self.assertEqual(len(paths), 5)
            frame = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
            self.assertEqual(len(frame), 122_171)
            self.assertTrue(frame["row_id"].is_unique)

    def test_tuning_notebook_code_cells_parse(self) -> None:
        path = PROJECT_ROOT / "notebooks" / "research" / "02_tuning_aninhado_s2.ipynb"
        notebook = json.loads(path.read_text(encoding="utf-8"))
        for cell in notebook["cells"]:
            if cell["cell_type"] == "code":
                ast.parse("".join(cell["source"]))


if __name__ == "__main__":
    unittest.main()
