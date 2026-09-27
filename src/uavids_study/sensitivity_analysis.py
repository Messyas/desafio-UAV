"""Separate paired sensitivity to clipping PacketDropRate; no simulator correction claim."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .feature_ablation import ROOT, aggregate, verified_records, validate_partitions
    from .paired_analysis import load_cell, paired_bootstrap, validated_probabilities
    from .predictive_experiment import file_hash, predictive_metrics, write_json
except ImportError:
    from feature_ablation import ROOT, aggregate, verified_records, validate_partitions
    from paired_analysis import load_cell, paired_bootstrap, validated_probabilities
    from predictive_experiment import file_hash, predictive_metrics, write_json


def validate_comparison(reference, sensitivity):
    for key in ("models", "primary_features", "class_order", "folds", "seeds", "threads"):
        if reference[key] != sensitivity[key]:
            raise ValueError(f"Clipping comparison changes another factor: {key}")
    if reference.get("clip_packet_drop_rate", False) or not sensitivity.get("clip_packet_drop_rate", False):
        raise ValueError("Expected original reference and explicitly clipped sensitivity")
    if sensitivity["conditions"] != {"A0": []} or reference["conditions"].get("A0") != []:
        raise ValueError("Compare only original features (A0)")
    if sensitivity["protocols"] != ["S2"] or "S2" not in reference["protocols"]:
        raise ValueError("This secondary analysis is frozen for S2")


def analyze(reference_path, sensitivity_path):
    reference = json.loads(Path(reference_path).read_text("utf-8"))
    sensitivity = json.loads(Path(sensitivity_path).read_text("utf-8"))
    validate_comparison(reference, sensitivity)
    outputs = [ROOT / "results" / config["experiment_id"] for config in (reference, sensitivity)]
    frozen = [json.loads((output / "frozen_protocol.json").read_text("utf-8")) for output in outputs]
    for key in ("dataset_sha256", "split_sha256", "code_sha256", "environment"):
        if frozen[0]["identity"][key] != frozen[1]["identity"][key]:
            raise ValueError(f"Paired experiments have different {key}")
    data_path = ROOT / sensitivity.get("dataset_path", "notebooks/data/raw/UAVIDS-2025.csv")
    split_path = ROOT / sensitivity.get("split_path", "research_artifacts/data_audit/split_candidates.csv.gz")
    if file_hash(data_path) != frozen[1]["identity"]["dataset_sha256"] or file_hash(split_path) != frozen[1]["identity"]["split_sha256"]:
        raise ValueError("Analysis data differ from frozen identity")
    data, splits = pd.read_csv(data_path), pd.read_csv(split_path)
    validate_partitions(data, splits, sensitivity)
    records = []
    manifests = []
    for output, config in zip(outputs, (reference, sensitivity)):
        manifests.append(aggregate(output, config))
        records.append(verified_records(output, config))
    options = sensitivity["analysis"]
    labels = sensitivity["class_order"]
    mapping = dict(zip(labels, range(len(labels))))
    y = data.label.map(mapping).to_numpy(dtype=int)
    rows = []
    for model in sensitivity["models"]:
        for seed in sensitivity["seeds"]:
            frames = [load_cell(output, saved, protocol="S2", model=model, seed=seed, condition="A0",
                config=config, data=data, splits=splits)
                for output, saved, config in zip(outputs, records, (reference, sensitivity))]
            predictions = np.stack([frame.y_pred.map(mapping).to_numpy(dtype=int) for frame in frames])
            scores = []
            for frame, pred in zip(frames, predictions):
                metrics, _, _ = predictive_metrics(y, pred, validated_probabilities(frame, labels), labels)
                scores.append(metrics["f1_macro"])
            result = paired_bootstrap(y, predictions, splits.s2_group.to_numpy(), classes=len(labels),
                replicates=options["bootstrap_replicates"], confidence=options["confidence"], seed=options["seed"])
            low, high = result["difference_intervals"][1]
            rows.append(dict(protocol="S2", model=model, seed=seed, original_f1=scores[0], clipped_f1=scores[1],
                f1_macro_delta=scores[1] - scores[0], ci_low=low, ci_high=high,
                groups=result["groups"], draws_missing_any_class=result["missing_class_draws"],
                uncertainty_scope="conditional_group_bootstrap_fixed_oof_secondary_sensitivity"))
    report = ROOT / "reports" / sensitivity["experiment_id"]
    report.mkdir(parents=True, exist_ok=True)
    path = report / "clipping_comparisons.csv"
    pd.DataFrame(rows).to_csv(path, index=False)
    reference_inputs = [{"job_id": record["job_id"], "prediction_sha256": record["prediction_sha256"]}
        for record in records[0] if record["protocol"] == "S2" and record["condition"] == "A0"]
    current_inputs = [{"job_id": record["job_id"], "prediction_sha256": record["prediction_sha256"]}
        for record in records[1]]
    write_json(report / "sensitivity_manifest.json", {"reference": reference["experiment_id"],
        "sensitivity": sensitivity["experiment_id"], "identities": [item["identity"] for item in frozen],
        "analysis": options, "output_sha256": {path.name: file_hash(path)},
        "analysis_code_sha256": file_hash(Path(__file__)),
        "reference_predictions": reference_inputs, "prediction_inputs": current_inputs,
        "interpretation": "Secondary sensitivity; does not establish that values above 1 are simulator errors."})
    write_json(report / "analysis_manifest.json", {"experiment_id": sensitivity["experiment_id"],
        "config_sha256": manifests[1]["config_sha256"], "dataset_sha256": manifests[1]["dataset_sha256"],
        "split_sha256": manifests[1]["split_sha256"], "protocols": ["S2"],
        "requested_protocols_complete": True, "whole_experiment_complete": manifests[1]["complete"],
        "analysis_code_sha256": file_hash(Path(__file__)), "analysis": options,
        "prediction_inputs": current_inputs, "output_sha256": {path.name: file_hash(path)},
        "reference_experiment": reference["experiment_id"],
        "reference_config_sha256": manifests[0]["config_sha256"],
        "reference_predictions": reference_inputs,
        "limits": ["Secondary paired clipping sensitivity, not a simulator correction claim.",
            "Intervals are conditional on fixed OOF predictions and do not measure retraining uncertainty."]})
    print(f"Verified clipping sensitivity written to {report}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-config", type=Path, default=ROOT / "configs/feature_ablation_v4.json")
    parser.add_argument("--config", type=Path, default=ROOT / "configs/pdr_sensitivity_v6.json")
    args = parser.parse_args()
    analyze(args.reference_config, args.config)


if __name__ == "__main__":
    main()
