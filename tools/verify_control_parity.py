"""Verify the new A0 control against saved historical baseline predictions."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.uavids_study.feature_ablation import verified_records
from src.uavids_study.predictive_experiment import file_hash, json_hash, write_json
from tools.export_mlflow import prepare_export


def verify():
    config_path = ROOT / "configs/feature_ablation_v4.json"
    historical_path = ROOT / "configs/predictive_baseline_v1.json"
    config = json.loads(config_path.read_text("utf-8"))
    experiment = ROOT / "results" / config["experiment_id"]
    manifest = json.loads((experiment / "experiment_manifest.json").read_text("utf-8"))
    if not manifest["complete"] or manifest["config_sha256"] != json_hash(config):
        raise ValueError("New A0 panel must be complete and match the frozen configuration")
    historical = ROOT / "results/predictive_baseline_v1"
    historical_manifest, historical_jobs = prepare_export(historical, historical_path)
    if historical_manifest["dataset_sha256"] != manifest["dataset_sha256"] or historical_manifest["split_sha256"] != manifest["split_sha256"]:
        raise ValueError("Control comparison uses different data or partitions")
    old = {item["record"]["job_id"]: item for item in historical_jobs}
    rows = []
    for record in verified_records(experiment, config):
        if record["condition"] != "A0":
            continue
        key = record["job_id"].removesuffix("__A0")
        previous = old[key]
        first = pd.read_csv(previous["prediction"])
        second_path = experiment / record["prediction_file"]
        second = pd.read_csv(second_path)
        columns = [name for name in first if name.startswith("probability__")]
        equal = (first.row_id.equals(second.row_id) and first.flow_id.equals(second.flow_id)
            and first.y_true.equals(second.y_true) and first.y_pred.equals(second.y_pred)
            and np.array_equal(first[columns].to_numpy(), second[columns].to_numpy()))
        rows.append(dict(protocol=record["protocol"], fold=record["fold"], model=record["model"],
            seed=record["seed"], rows=len(first), exact_equal=equal,
            historical_prediction_sha256=previous["record"]["prediction_sha256"],
            new_prediction_sha256=record["prediction_sha256"]))
    expected = len(config["protocols"]) * len(config["folds"]) * len(config["models"]) * len(config["seeds"])
    if len(rows) != expected:
        raise ValueError("Missing A0 control jobs")
    report = ROOT / "reports" / config["experiment_id"]
    report.mkdir(exist_ok=True)
    table = report / "control_parity.csv"
    pd.DataFrame(rows).to_csv(table, index=False)
    write_json(report / "control_parity_manifest.json", {"historical_config_sha256": historical_manifest["config_sha256"],
        "new_config_sha256": manifest["config_sha256"], "dataset_sha256": manifest["dataset_sha256"],
        "split_sha256": manifest["split_sha256"], "jobs": len(rows),
        "exact_equal_jobs": sum(row["exact_equal"] for row in rows),
        "table_sha256": file_hash(table), "code_sha256": file_hash(Path(__file__)),
        "interpretation": "Numerical equivalence check, not a new independent evaluation."})
    if not all(row["exact_equal"] for row in rows):
        raise ValueError("Some new A0 controls differ from the historical baseline; inspect the report")
    print(f"Exact A0 parity: {len(rows)}/{len(rows)} jobs")


if __name__ == "__main__":
    verify()
