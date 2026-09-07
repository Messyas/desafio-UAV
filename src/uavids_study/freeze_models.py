"""Fit and freeze full-data model artifacts for systems benchmarks only."""

from __future__ import annotations

import json
import pickle
import platform
import sys
import time
import warnings
from importlib.metadata import version
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from uavids_study.predictive_experiment import (  # type: ignore
        build_estimator,
        file_hash,
        json_hash,
        write_json,
    )
else:
    from .predictive_experiment import build_estimator, file_hash, json_hash, write_json


def freeze_models(project_root: Path, config_path: Path, force: bool = False) -> dict:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config_sha256 = json_hash(config)
    dataset_path = project_root / "notebooks" / "data" / "raw" / "UAVIDS-2025.csv"
    output_dir = project_root / "artifacts" / "models" / config["artifact_set_id"]
    manifest_path = output_dir / "manifest.json"
    if not force and manifest_path.exists():
        existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        valid = existing.get("config_sha256") == config_sha256
        for model in existing.get("models", []):
            path = output_dir / model["file"]
            valid = valid and path.exists() and file_hash(path) == model["sha256"]
        if valid and len(existing.get("models", [])) == len(config["models"]):
            print(f"Frozen artifacts already valid: {output_dir}")
            return existing

    output_dir.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(dataset_path)
    features = list(config["features"])
    class_order = list(config["class_order"])
    class_to_id = {name: index for index, name in enumerate(class_order)}
    y = data["label"].map(class_to_id).to_numpy(dtype=np.int8)
    x = data[features].to_numpy(dtype=np.float64)
    model_records = []
    for model_name, model_config in config["models"].items():
        estimator = build_estimator(
            model_name,
            model_config,
            seed=int(config["random_seed"]),
            threads=int(config["threads"]),
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with threadpool_limits(limits=int(config["threads"])):
                start = time.perf_counter()
                estimator.fit(x, y)
                fit_seconds = time.perf_counter() - start
                smoke_probabilities = estimator.predict_proba(x[:100])
        if smoke_probabilities.shape != (100, len(class_order)):
            raise AssertionError("Frozen model returned an unexpected probability shape")
        if not np.allclose(smoke_probabilities.sum(axis=1), 1.0, atol=1e-6):
            raise AssertionError("Frozen model probabilities do not sum to one")
        artifact_path = output_dir / f"{model_name}.pkl"
        artifact_path.write_bytes(
            pickle.dumps(estimator, protocol=pickle.HIGHEST_PROTOCOL)
        )
        model_records.append(
            {
                "model": model_name,
                "file": artifact_path.name,
                "sha256": file_hash(artifact_path),
                "bytes": artifact_path.stat().st_size,
                "fit_seconds": fit_seconds,
                "warnings": [
                    {"category": item.category.__name__, "message": str(item.message)}
                    for item in caught
                ],
            }
        )
        print(
            f"FROZEN {model_name} bytes={artifact_path.stat().st_size} "
            f"fit={fit_seconds:.2f}s"
        )

    schema = {
        "input_dtype": "float64",
        "input_shape": [None, len(features)],
        "features": features,
        "output": "predict_proba",
        "class_order": class_order,
    }
    write_json(output_dir / "schema.json", schema)
    manifest = {
        "artifact_set_id": config["artifact_set_id"],
        "purpose": config["purpose"],
        "config_sha256": config_sha256,
        "dataset_sha256": file_hash(dataset_path),
        "training_rows": len(data),
        "predictive_metrics_computed_on_training_data": False,
        "models": model_records,
        "schema_sha256": file_hash(output_dir / "schema.json"),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": version("scikit-learn"),
            "xgboost": version("xgboost"),
            "platform": platform.platform(),
        },
    }
    write_json(manifest_path, manifest)
    return manifest


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    config_path = project_root / "configs" / "deployment_candidates_v1.json"
    freeze_models(project_root, config_path)


if __name__ == "__main__":
    main()
