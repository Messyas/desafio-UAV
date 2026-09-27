"""Frozen paired ablation runner. Historical outputs are never reused as controls."""
from __future__ import annotations

import argparse
import itertools
import json
import platform
import sys
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd

try:
    from .predictive_experiment import file_hash, json_hash, run_job, validate_experiment_inputs, write_json
    from .features import RATIOS
except ImportError:
    from predictive_experiment import file_hash, json_hash, run_job, validate_experiment_inputs, write_json
    from features import RATIOS

ROOT = Path(__file__).resolve().parents[2]


def job_grid(config):
    return list(itertools.product(config["protocols"], config["folds"],
        [name for name, value in config["models"].items() if value.get("enabled", True)],
        config["seeds"], config["conditions"]))


def job_id(cell):
    protocol, fold, model, seed, condition = cell
    return f"{protocol.lower()}__fold_{fold}__{model}__seed_{seed}__{condition}"


def validate_config(config):
    if config.get("experiment_kind") != "feature_ablation":
        raise ValueError("Expected a feature_ablation configuration")
    if config["conditions"].get("A0") != []:
        raise ValueError("A0 must contain only original features")
    for key in ("protocols", "folds", "seeds", "class_order", "primary_features"):
        if not config[key] or len(set(config[key])) != len(config[key]):
            raise ValueError(f"Empty or repeated {key}")
    if set(config["protocols"]) - {"S0", "S1", "S2"}:
        raise ValueError("Unknown protocol")
    if len(config["class_order"]) != 5 or "Normal Traffic" not in config["class_order"]:
        raise ValueError("The primary task requires five classes")
    if set(config["primary_features"]) & {"FlowID", "SrcAddr", "DstAddr", "Protocol", "label"}:
        raise ValueError("Identifiers and labels cannot enter the ablation")
    if config["threads"] < 1 or len(config["folds"]) < 2:
        raise ValueError("Invalid threads or fold count")
    for derived in config["conditions"].values():
        if len(set(derived)) != len(derived) or set(derived) - RATIOS.keys():
            raise ValueError("Unknown or repeated derived feature")
        for name in derived:
            if not set(RATIOS[name]).issubset(config["primary_features"]):
                raise ValueError("Missing formula inputs")
    if not config["models"] or set(config["models"]) - {"random_forest", "xgboost"}:
        raise ValueError("Primary ablation supports RF and XGBoost")
    if any(value.get("additional_features") for value in config["models"].values()):
        raise ValueError("Additional model-specific features would confound the ablation")
    if any(not value.get("enabled", True) for value in config["models"].values()):
        raise ValueError("Remove disabled models from the frozen plan")
    if "baseline_config_sha256" in config:
        baseline = json.loads((ROOT / "configs/predictive_baseline_v1.json").read_text("utf-8"))
        if json_hash(baseline) != config["baseline_config_sha256"]:
            raise ValueError("Historical baseline configuration changed")
        if any(config[key] != baseline[key] for key in ("primary_features", "class_order")):
            raise ValueError("Ablation must preserve the baseline feature and label contract")
        if any(value != baseline["models"][name] for name, value in config["models"].items()):
            raise ValueError("Ablation must use the fixed baseline hyperparameters")
    if Path(config["experiment_id"]).name != config["experiment_id"] or config["experiment_id"] in {".", ".."}:
        raise ValueError("experiment_id must be a directory name")


def validate_partitions(data, splits, config):
    if len(data) != len(splits) or not np.array_equal(splits.row_id, np.arange(len(data))):
        raise ValueError("Row identities differ from partitions")
    if not np.array_equal(data.FlowID.to_numpy(), splits.flow_id.to_numpy()):
        raise ValueError("Flow identities differ from partitions")
    if not np.array_equal(data.label.to_numpy(), splits.label.to_numpy()):
        raise ValueError("Labels differ from partitions")
    if set(data.label) != set(config["class_order"]):
        raise ValueError("Unexpected or absent class")
    signatures = pd.util.hash_pandas_object(data[config["primary_features"]], index=False)
    for protocol in config["protocols"]:
        column = protocol.lower() + "_fold"
        if set(splits[column]) != set(config["folds"]):
            raise ValueError("Configured folds must cover the complete partition")
        if protocol != "S0":
            actual_groups = signatures if protocol == "S1" else data.SrcAddr
            if pd.DataFrame({"group": np.asarray(actual_groups), "fold": splits[column]}).groupby("group").fold.nunique().max() != 1:
                raise ValueError(f"Groups leak across {protocol} folds")
            saved = "s1_group" if protocol == "S1" else "s2_group"
            mapping = pd.DataFrame({"actual": np.asarray(actual_groups), "saved": splits[saved]})
            if mapping.groupby("actual").saved.nunique().max() != 1 or mapping.groupby("saved").actual.nunique().max() != 1:
                raise ValueError(f"Saved {protocol} group mapping is inconsistent")
        for fold in config["folds"]:
            mask = splits[column] == fold
            if set(data.loc[mask, "label"]) != set(config["class_order"]) or set(data.loc[~mask, "label"]) != set(config["class_order"]):
                raise ValueError(f"Absent class in {protocol} fold {fold}")


def freeze(config, dataset, splits, output):
    validate_experiment_inputs(dataset, splits, output)
    identity = {
        "config_sha256": json_hash(config), "dataset_sha256": file_hash(dataset),
        "split_sha256": file_hash(splits),
        "code_sha256": {name: file_hash(Path(__file__).with_name(name)) for name in
            ("feature_ablation.py", "features.py", "predictive_experiment.py")},
        "environment": {"python": sys.version, "platform": platform.platform(),
            "packages": {name: version(name) for name in
                ("numpy", "pandas", "scikit-learn", "scipy", "xgboost", "threadpoolctl")}},
    }
    path = output / "frozen_protocol.json"
    if path.exists() and json.loads(path.read_text("utf-8"))["identity"] != identity:
        raise ValueError("Frozen data/config/code/environment changed; use a new experiment_id")
    if not path.exists():
        write_json(path, {"identity": identity, "config": config,
            "interpretation": "Exploratory: existing folds and dataset have already been inspected."})
    return identity


def verified_records(output, config):
    expected = {job_id(cell) for cell in job_grid(config)}
    records = []
    for path in sorted((output / "job_records").glob("*.json")):
        record = json.loads(path.read_text("utf-8"))
        if record.get("status") != "complete":
            continue
        if record.get("job_id") not in expected or record.get("config_sha256") != json_hash(config):
            raise ValueError(f"Unexpected or mixed job: {path}")
        cell = tuple(record[key] for key in ("protocol", "fold", "model", "seed", "condition"))
        if job_id(cell) != record["job_id"] or path.stem != record["job_id"]:
            raise ValueError(f"Job metadata differ from identity: {path}")
        prediction = (output / record["prediction_file"]).resolve()
        if not prediction.is_relative_to(output.resolve()) or file_hash(prediction) != record["prediction_sha256"]:
            raise ValueError(f"Invalid prediction artifact: {path}")
        records.append(record)
    if len({record["job_id"] for record in records}) != len(records):
        raise ValueError("Duplicate jobs")
    return records


def aggregate(output, config):
    frozen = json.loads((output / "frozen_protocol.json").read_text("utf-8"))
    if frozen["config"] != config:
        raise ValueError("Configuration differs from frozen protocol")
    records = verified_records(output, config)
    rows = []
    for record in records:
        rows.append({**{key: record[key] for key in ("protocol", "fold", "model", "seed", "condition")},
            **record["metrics"], **{key: record[key] for key in
                ("train_rows", "test_rows", "fit_seconds", "inference_seconds", "serialized_model_bytes")}})
    if rows:
        pd.DataFrame(rows).to_csv(output / "fold_metrics.csv", index=False)
    completed = {record["job_id"] for record in records}
    missing = sorted({job_id(cell) for cell in job_grid(config)} - completed)
    manifest = {**frozen["identity"], "experiment_id": config["experiment_id"],
        "experiment_kind": "feature_ablation", "status": config["status"],
        "class_order": config["class_order"], "completed_jobs": len(records),
        "expected_jobs": len(job_grid(config)), "complete": not missing, "missing_jobs": missing}
    write_json(output / "experiment_manifest.json", manifest)
    return manifest


def run(config_path, *, protocols=None, folds=None, models=None, conditions=None, seeds=None, dry_run=False):
    config = json.loads(Path(config_path).read_text("utf-8"))
    validate_config(config)
    selections = dict(protocols=protocols, folds=folds, models=models, seeds=seeds, conditions=conditions)
    for key, selected in selections.items():
        allowed = config[key]
        if selected is not None and (not selected or set(selected) - set(allowed)):
            raise ValueError(f"Unknown or empty selection: {key}")
    cells = [cell for cell in job_grid(config) if all(selected is None or value in selected
        for value, selected in zip(cell, selections.values()))]
    if dry_run:
        print(json.dumps({"experiment": config["experiment_id"], "requested_jobs": len(cells),
            "planned_jobs": len(job_grid(config)), "jobs": [job_id(cell) for cell in cells]}, indent=2))
        return
    dataset = ROOT / config.get("dataset_path", "notebooks/data/raw/UAVIDS-2025.csv")
    split_path = ROOT / config.get("split_path", "research_artifacts/data_audit/split_candidates.csv.gz")
    output = ROOT / "results" / config["experiment_id"]
    data, splits = pd.read_csv(dataset), pd.read_csv(split_path)
    validate_partitions(data, splits, config)
    freeze(config, dataset, split_path, output)
    verified_records(output, config)  # Corruption fails instead of silently retraining.
    try:
        for protocol, fold, model, seed, condition in cells:
            run_job(data, splits, config, json_hash(config), output, protocol=protocol,
                fold=fold, model_name=model, seed_override=seed, condition=condition)
    finally:
        manifest = aggregate(output, config)
        print(f"Verified jobs: {manifest['completed_jobs']}/{manifest['expected_jobs']}", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/feature_ablation_v4.json")
    for key in ("protocols", "folds", "models", "conditions", "seeds"):
        parser.add_argument("--" + key, help="Comma-separated selection; full frozen plan remains unchanged")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    selected = {key: None if getattr(args, key) is None else getattr(args, key).split(",")
        for key in ("protocols", "folds", "models", "conditions", "seeds")}
    for key in ("folds", "seeds"):
        if selected[key] is not None:
            selected[key] = [int(value) for value in selected[key]]
    run(args.config, dry_run=args.dry_run, **selected)


if __name__ == "__main__":
    main()
