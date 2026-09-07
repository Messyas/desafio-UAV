from __future__ import annotations

import gzip
import hashlib
import json
import ast
import unittest
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_PATH = PROJECT_ROOT / "notebooks" / "data" / "raw" / "UAVIDS-2025.csv"
ARTIFACT_DIR = PROJECT_ROOT / "research_artifacts" / "data_audit"


class DataAuditArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.summary = json.loads(
            (ARTIFACT_DIR / "data_audit_summary.json").read_text(encoding="utf-8")
        )
        cls.manifest = json.loads(
            (ARTIFACT_DIR / "data_manifest.json").read_text(encoding="utf-8")
        )
        with gzip.open(ARTIFACT_DIR / "split_candidates.csv.gz", "rt") as stream:
            cls.splits = pd.read_csv(stream)
        cls.fold_balance = pd.read_csv(ARTIFACT_DIR / "fold_balance.csv")

    def test_local_file_identity_matches_registered_artifact(self) -> None:
        sha256 = hashlib.sha256(DATASET_PATH.read_bytes()).hexdigest()
        self.assertEqual(
            sha256,
            "d50d339f68be7b23f0bf089dd438b20a1835c13182d8641220538121440164d0",
        )
        self.assertTrue(
            self.manifest["dataset"]["exact_match_to_registered_zenodo_v1"]
        )

    def test_split_artifact_matches_registered_hash(self) -> None:
        split_path = ARTIFACT_DIR / "split_candidates.csv.gz"
        observed = hashlib.sha256(split_path.read_bytes()).hexdigest()
        self.assertEqual(observed, self.manifest["candidate_split_artifact"]["sha256"])

    def test_every_row_has_one_valid_fold_per_protocol(self) -> None:
        self.assertEqual(len(self.splits), self.summary["rows"])
        self.assertTrue(self.splits["row_id"].is_unique)
        for column in ("s0_fold", "s1_fold", "s2_fold"):
            self.assertEqual(set(self.splits[column].unique()), set(range(5)))
            self.assertFalse(self.splits[column].isna().any())

    def test_train_and_test_flow_ids_are_disjoint(self) -> None:
        for column in ("s0_fold", "s1_fold", "s2_fold"):
            for fold_id in range(5):
                test_ids = set(self.splits.loc[self.splits[column] == fold_id, "flow_id"])
                train_ids = set(self.splits.loc[self.splits[column] != fold_id, "flow_id"])
                self.assertTrue(test_ids.isdisjoint(train_ids))

    def test_constrained_groups_never_cross_folds(self) -> None:
        pairs = (("s1_group", "s1_fold"), ("s2_group", "s2_fold"))
        for group_column, fold_column in pairs:
            folds_per_group = self.splits.groupby(group_column)[fold_column].nunique()
            self.assertEqual(int((folds_per_group > 1).sum()), 0)

    def test_random_reference_exposes_repeated_signatures(self) -> None:
        folds_per_signature = self.splits.groupby("s1_group")["s0_fold"].nunique()
        self.assertGreater(int((folds_per_signature > 1).sum()), 0)

    def test_all_classes_are_present_in_every_candidate_fold(self) -> None:
        expected = set(self.splits["label"].unique())
        observed = self.fold_balance.groupby(["protocol", "fold"])["label"].agg(set)
        self.assertTrue(observed.map(lambda labels: labels == expected).all())

    def test_notebook_is_valid_json_and_code_cells_parse(self) -> None:
        notebook_path = (
            PROJECT_ROOT / "notebooks" / "research" / "00_auditoria_e_protocolo.ipynb"
        )
        notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
        self.assertEqual(notebook["nbformat"], 4)
        code_cells = [cell for cell in notebook["cells"] if cell["cell_type"] == "code"]
        self.assertGreater(len(code_cells), 0)
        for cell in code_cells:
            ast.parse("".join(cell["source"]))


if __name__ == "__main__":
    unittest.main()
