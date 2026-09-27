"""Verify saved predictions and rebuild derived metrics without training."""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.uavids_study.predictive_experiment import (
    predictive_metrics, validate_experiment_inputs, write_aggregates, write_json,
)
from tools.export_mlflow import prepare_export


def rebuild_metrics(project_root: Path, config_path: Path) -> dict:
    config = json.loads(config_path.read_text("utf-8"))
    if config.get("experiment_kind") == "feature_ablation":
        raise ValueError("Use paired_analysis.py for ablations: it verifies complete paired OOF coverage")
    output_dir = project_root / "results" / config["experiment_id"]
    original, jobs = prepare_export(output_dir, config_path)
    dataset = project_root / "notebooks" / "data" / "raw" / "UAVIDS-2025.csv"
    splits = project_root / "research_artifacts" / "data_audit" / "split_candidates.csv.gz"
    validate_experiment_inputs(dataset, splits, output_dir)
    classes = config["class_order"]
    mapping = {name: index for index, name in enumerate(classes)}
    columns = [f"probability__{name.lower().replace(' ', '_')}" for name in classes]
    for job in jobs:
        record = job["record"]
        predictions = pd.read_csv(job["prediction"])
        if not predictions["row_id"].is_unique:
            raise ValueError(f"Duplicated prediction rows: {record['job_id']}")
        labels = predictions[["y_true", "y_pred"]].apply(lambda values: values.map(mapping))
        if labels.isna().any().any():
            raise ValueError(f"Unknown class in {record['job_id']}")
        probabilities = predictions[columns].to_numpy(dtype=float)
        if not np.isfinite(probabilities).all() or (probabilities < 0).any():
            raise ValueError(f"Invalid probabilities: {record['job_id']}")
        totals = probabilities.sum(axis=1, keepdims=True)
        if (totals <= 0).any():
            raise ValueError(f"Zero probability mass: {record['job_id']}")
        metrics, _, _ = predictive_metrics(
            labels["y_true"].to_numpy(dtype=np.int8),
            labels["y_pred"].to_numpy(dtype=np.int8),
            probabilities / totals, classes,
        )
        for key, observed in metrics.items():
            expected = record["metrics"][key]
            if not math.isclose(observed, expected, rel_tol=1e-6, abs_tol=1e-8):
                raise ValueError(f"Recorded metric {key} differs in {record['job_id']}")
    regenerated = write_aggregates(
        output_dir, config, original["config_sha256"], dataset, splits
    )
    # Reaggregation is not a new training run. Preserve its historical environment.
    regenerated["aggregation_environment"] = regenerated["environment"]
    regenerated["environment"] = original["environment"]
    regenerated["aggregation_verified_at_utc"] = datetime.now(timezone.utc).isoformat()
    write_json(output_dir / "experiment_manifest.json", regenerated)
    return {"experiment": config["experiment_id"], "verified_jobs": len(jobs)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(rebuild_metrics(ROOT, args.config.resolve()), indent=2))


if __name__ == "__main__":
    main()
