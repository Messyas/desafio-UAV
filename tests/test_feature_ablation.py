from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from sklearn.base import clone
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline

from src.uavids_study import feature_ablation as runner
from src.uavids_study import paired_analysis as analysis
from src.uavids_study import sensitivity_analysis as sensitivity
from src.uavids_study.features import DerivedFeatures
from src.uavids_study.predictive_experiment import file_hash, write_json

ROOT = Path(__file__).resolve().parents[1]


class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.columns = ["LostPackets", "TxPackets", "RxBytes", "TxBytes", "Throughput/Kbps", "AverageHopCount", "PacketDropRate"]
        self.frame = pd.DataFrame([[2, 4, 6, 12, 20, 2, 1.5], [1, 0, 2, -1, 10, 0, .4]], columns=self.columns, dtype=float)

    def test_formulas_and_invalid_denominators(self):
        transform = DerivedFeatures(self.columns, ["loss_ratio", "tx_efficiency", "throughput_per_hop"])
        values = clone(transform).fit_transform(self.frame)
        np.testing.assert_allclose(values[0, -3:], [.5, .5, 10])
        self.assertTrue(np.isnan(values[1, -3:]).all())
        np.testing.assert_equal(values[:, :7], self.frame.to_numpy())

    def test_test_values_cannot_change_training_imputation(self):
        pipeline = Pipeline([("features", DerivedFeatures(self.columns, ["loss_ratio"])),
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True))])
        pipeline.fit(self.frame)
        test = self.frame.copy()
        test.loc[0, ["LostPackets", "TxPackets"]] = [999, 1]
        result = pipeline.transform(test)
        self.assertEqual(result[1, -1], .5)
        self.assertEqual(pipeline.named_steps["imputer"].statistics_[-1], .5)

    def test_all_missing_training_derivative_keeps_dimension_and_zero_fallback(self):
        self.frame["TxPackets"] = 0
        pipeline = Pipeline([("features", DerivedFeatures(self.columns, ["loss_ratio"])),
            ("imputer", SimpleImputer(strategy="median", keep_empty_features=True))])
        result = pipeline.fit_transform(self.frame)
        self.assertEqual(result.shape, (2, 8))
        self.assertTrue((result[:, -1] == 0).all())

    def test_overflow_becomes_missing_and_raw_infinity_is_rejected(self):
        self.frame.loc[0, ["LostPackets", "TxPackets"]] = [1e308, 1e-308]
        transform = DerivedFeatures(self.columns, ["loss_ratio"])
        self.assertTrue(np.isnan(transform.fit_transform(self.frame)[0, -1]))
        self.frame.loc[0, "LostPackets"] = np.inf
        with self.assertRaisesRegex(ValueError, "finite"):
            transform.fit(self.frame)

    def test_clipping_is_explicit_and_does_not_mutate_input(self):
        original = self.frame.copy()
        values = DerivedFeatures(self.columns, clip_packet_drop_rate=True).fit_transform(self.frame)
        self.assertEqual(values[0, -1], 1)
        pd.testing.assert_frame_equal(self.frame, original)
        with self.assertRaisesRegex(ValueError, "order"):
            DerivedFeatures(self.columns).fit(self.frame[self.columns[::-1]])


class BootstrapTests(unittest.TestCase):
    def test_probability_rounding_is_normalized_but_invalid_mass_is_rejected(self):
        frame = pd.DataFrame({"probability__a": [.2], "probability__b": [.80000002]})
        result = analysis.validated_probabilities(frame, ["a", "b"])
        np.testing.assert_allclose(result.sum(axis=1), [1], rtol=0, atol=1e-15)
        self.assertEqual(result.argmax(axis=1)[0], 1)
        frame["probability__b"] = .9
        with self.assertRaisesRegex(ValueError, "Invalid class probabilities"):
            analysis.validated_probabilities(frame, ["a", "b"])

    def test_whole_unequal_groups_have_known_paired_differences(self):
        result = analysis.paired_bootstrap(np.array([0, 0, 1]),
            np.array([[0, 0, 0], [0, 0, 1]]), np.array(["a", "a", "b"]),
            classes=2, replicates=2000, confidence=.95, seed=12)
        differences = np.round(result["draws"][:, 1] - result["draws"][:, 0], 8)
        self.assertEqual(set(differences), {0, .5, .6})
        np.testing.assert_allclose(result["difference_intervals"][1], [0, .6])
        self.assertEqual(result["groups"], 2)
        self.assertGreater(result["missing_class_draws"], 0)

    def test_identical_predictions_have_exact_zero_difference(self):
        result = analysis.paired_bootstrap(np.array([0, 1, 0, 1]),
            np.array([[0, 1, 1, 1], [0, 1, 1, 1]]), np.array([0, 0, 1, 1]),
            classes=2, replicates=30, confidence=.95, seed=1)
        np.testing.assert_equal(result["difference_intervals"], np.zeros((2, 2)))

    def test_rejects_unpaired_arrays_and_single_group(self):
        with self.assertRaisesRegex(ValueError, "Unpaired"):
            analysis.paired_bootstrap(np.array([0, 1]), np.array([[0]]), np.array([0, 1]), classes=2, replicates=3, confidence=.95, seed=1)
        with self.assertRaisesRegex(ValueError, "two groups"):
            analysis.paired_bootstrap(np.array([0, 1]), np.array([[0, 1]]), np.array([0, 0]), classes=2, replicates=3, confidence=.95, seed=1)


class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = json.loads((ROOT / "configs/feature_ablation_v4.json").read_text())
        self.config.pop("baseline_config_sha256")
        self.config.update(experiment_id="synthetic_only", protocols=["S2"], folds=[0, 1], threads=1,
            dataset_path="data.csv", split_path="split.csv", models={"random_forest": {
                "enabled": True, "parameters": {"n_estimators": 3, "max_depth": 2}}})
        self.config["analysis"]["bootstrap_replicates"] = 30
        features = self.config["primary_features"]
        rows = []
        for group in range(4):
            for class_id, label in enumerate(self.config["class_order"]):
                row_id = len(rows)
                rows.append({**dict(zip(features, [row_id + 1] * len(features))),
                    "FlowID": row_id + 1, "SrcAddr": "src_" + str(group), "label": label})
        self.data = pd.DataFrame(rows)
        self.splits = pd.DataFrame({"row_id": np.arange(20), "flow_id": self.data.FlowID,
            "label": self.data.label, "s1_group": np.arange(20), "s2_group": np.repeat(np.arange(4), 5),
            "s2_fold": np.repeat(np.arange(4) % 2, 5)})
        self.data.to_csv(self.root / "data.csv", index=False)
        self.splits.to_csv(self.root / "split.csv", index=False)
        self.path = self.root / "config.json"
        write_json(self.path, self.config)
        self.output = self.root / "results/synthetic_only"

    def run_jobs(self, **kwargs):
        with patch.object(runner, "ROOT", self.root):
            runner.run(self.path, **kwargs)

    def test_end_to_end_resume_analysis_and_corruption(self):
        self.run_jobs()
        self.assertTrue(runner.aggregate(self.output, self.config)["complete"])
        with patch("sklearn.pipeline.Pipeline.fit", side_effect=AssertionError("Must not retrain")):
            self.run_jobs()
        with patch.object(analysis, "ROOT", self.root):
            analysis.analyze(self.path)
        report = self.root / "reports/synthetic_only"
        self.assertEqual(len(pd.read_csv(report / "paired_comparisons.csv")), 4)
        normalized = pd.read_csv(report / "confusion_normalized.csv")
        totals = normalized.groupby(["protocol", "model", "seed", "condition", "true_class_id"])["fraction_of_true_class"].sum()
        np.testing.assert_allclose(totals.to_numpy(), np.ones(len(totals)))
        record = runner.verified_records(self.output, self.config)[0]
        prediction = self.output / record["prediction_file"]
        prediction.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "Invalid prediction"):
            self.run_jobs()

    def test_partial_run_is_not_analyzable(self):
        self.run_jobs(folds=[0], conditions=["A0"])
        self.assertFalse(runner.aggregate(self.output, self.config)["complete"])
        with patch.object(analysis, "ROOT", self.root), self.assertRaisesRegex(ValueError, "Incomplete OOF"):
            analysis.analyze(self.path)
        self.assertFalse((self.root / "reports/synthetic_only/pooled_metrics.csv").exists())

    def test_frozen_config_change_requires_new_experiment(self):
        self.run_jobs(folds=[0], conditions=["A0"])
        self.config["models"]["random_forest"]["parameters"]["n_estimators"] = 4
        write_json(self.path, self.config)
        with self.assertRaisesRegex(ValueError, "Frozen"):
            self.run_jobs()

    def test_group_leakage_and_label_misalignment_are_rejected(self):
        splits = self.splits.copy()
        splits.loc[0, "s2_fold"] = 1
        with self.assertRaisesRegex(ValueError, "leak"):
            runner.validate_partitions(self.data, splits, self.config)
        splits = self.splits.copy()
        splits.loc[0, "label"] = self.config["class_order"][1]
        with self.assertRaisesRegex(ValueError, "Labels"):
            runner.validate_partitions(self.data, splits, self.config)

    def test_rejects_identifier_features_and_changed_fixed_parameters(self):
        changed = copy.deepcopy(self.config)
        changed["primary_features"].append("FlowID")
        with self.assertRaisesRegex(ValueError, "Identifiers"):
            runner.validate_config(changed)
        fixed = json.loads((ROOT / "configs/feature_ablation_v4.json").read_text())
        fixed["models"]["random_forest"]["parameters"]["n_estimators"] = 240
        with self.assertRaisesRegex(ValueError, "fixed baseline"):
            runner.validate_config(fixed)

    def test_predicted_row_swap_is_detected_even_with_new_checksum(self):
        self.run_jobs()
        record = runner.verified_records(self.output, self.config)[0]
        path = self.output / record["prediction_file"]
        frame = pd.read_csv(path)
        frame.loc[0, "flow_id"] = -99
        frame.to_csv(path, index=False, compression="gzip")
        record["prediction_sha256"] = file_hash(path)
        write_json(self.output / "job_records" / (record["job_id"] + ".json"), record)
        with patch.object(analysis, "ROOT", self.root), self.assertRaisesRegex(ValueError, "identity"):
            analysis.analyze(self.path)

    def test_clipping_sensitivity_uses_identical_control_and_complete_pairs(self):
        self.run_jobs()
        clipped = copy.deepcopy(self.config)
        clipped.update(experiment_id="synthetic_clipped", conditions={"A0": []}, clip_packet_drop_rate=True)
        clipped_path = self.root / "clipped.json"
        write_json(clipped_path, clipped)
        with patch.object(runner, "ROOT", self.root):
            runner.run(clipped_path)
        with patch.object(sensitivity, "ROOT", self.root):
            sensitivity.analyze(self.path, clipped_path)
        table = pd.read_csv(self.root / "reports/synthetic_clipped/clipping_comparisons.csv")
        self.assertEqual(len(table), 1)
        manifest = json.loads((self.root / "reports/synthetic_clipped/analysis_manifest.json").read_text())
        self.assertEqual(manifest["reference_experiment"], "synthetic_only")
        self.assertEqual(len(manifest["reference_predictions"]), 2)
        self.assertTrue(np.isfinite(table[["f1_macro_delta", "ci_low", "ci_high"]]).all().all())
        clipped["threads"] = 2
        with self.assertRaisesRegex(ValueError, "another factor"):
            sensitivity.validate_comparison(self.config, clipped)

    def test_saved_group_mapping_cannot_merge_different_origins(self):
        splits = self.splits.copy()
        splits.loc[splits.s2_group == 2, "s2_group"] = 0
        with self.assertRaisesRegex(ValueError, "mapping"):
            runner.validate_partitions(self.data, splits, self.config)

    def test_complete_three_protocols_produce_aligned_protocol_contrasts(self):
        self.config["protocols"] = ["S0", "S1", "S2"]
        self.splits["s0_fold"] = self.splits.s2_fold
        self.splits["s1_fold"] = self.splits.s2_fold
        self.splits.to_csv(self.root / "split.csv", index=False)
        write_json(self.path, self.config)
        self.run_jobs()
        with patch.object(analysis, "ROOT", self.root):
            analysis.analyze(self.path)
        path = self.root / "reports/synthetic_only/protocol_comparisons.csv"
        comparisons = pd.read_csv(path)
        self.assertEqual(len(comparisons), 15)
        self.assertTrue((comparisons.f1_macro_delta == 0).all())
        self.assertTrue((comparisons.ci_low == 0).all())
        self.assertTrue((comparisons.ci_high == 0).all())

    def test_three_seed_analysis_reports_descriptive_variation(self):
        self.config["seeds"] = [11, 12, 13]
        write_json(self.path, self.config)
        self.run_jobs()
        with patch.object(analysis, "ROOT", self.root):
            analysis.analyze(self.path)
        variation = pd.read_csv(self.root / "reports/synthetic_only/seed_variation.csv")
        self.assertEqual(len(variation), 5)
        self.assertTrue((variation.seed_count == 3).all())
        self.assertEqual(variation.loc[variation.condition == "A0", "delta_seed_mean"].item(), 0)


if __name__ == "__main__":
    unittest.main()
