"""Measure frozen model inference in isolated local processes."""

from __future__ import annotations

import argparse
import gc
import json
import pickle
import platform
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import psutil
from threadpoolctl import threadpool_limits

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from uavids_study.predictive_experiment import (  # type: ignore
        file_hash,
        json_hash,
        write_gzip_csv,
        write_json,
    )
else:
    from .predictive_experiment import file_hash, json_hash, write_gzip_csv, write_json


def distribution_summary(values_ns: np.ndarray) -> dict[str, float]:
    values_us = values_ns.astype(np.float64) / 1_000
    return {
        "count": int(len(values_us)),
        "mean_us": float(values_us.mean()),
        "std_us": float(values_us.std(ddof=1)),
        "p50_us": float(np.quantile(values_us, 0.50)),
        "p95_us": float(np.quantile(values_us, 0.95)),
        "p99_us": float(np.quantile(values_us, 0.99)),
        "max_us": float(values_us.max()),
    }


def benchmark_model(
    project_root: Path, config_path: Path, model_name: str
) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    if model_name not in config["models"]:
        raise ValueError(f"Model not listed in benchmark config: {model_name}")
    artifact_dir = (
        project_root / "artifacts" / "models" / config["artifact_set_id"]
    )
    artifact_manifest = json.loads(
        (artifact_dir / "manifest.json").read_text(encoding="utf-8")
    )
    schema = json.loads((artifact_dir / "schema.json").read_text(encoding="utf-8"))
    model_record = next(
        item for item in artifact_manifest["models"] if item["model"] == model_name
    )
    model_path = artifact_dir / model_record["file"]
    if file_hash(model_path) != model_record["sha256"]:
        raise AssertionError("Model hash differs from frozen manifest")

    dataset_path = project_root / "notebooks" / "data" / "raw" / "UAVIDS-2025.csv"
    inputs = pd.read_csv(dataset_path, usecols=schema["features"])[
        schema["features"]
    ].to_numpy(dtype=np.float64)
    rng = np.random.default_rng(int(config["random_seed"]))
    process = psutil.Process()
    rss_before_load = process.memory_info().rss
    load_start = time.perf_counter()
    # Loading pickle is safe only because the artifact was generated and hashed locally.
    model = pickle.loads(model_path.read_bytes())
    load_seconds = time.perf_counter() - load_start
    rss_after_load = process.memory_info().rss

    warmup_indices = rng.integers(0, len(inputs), size=int(config["warmup_calls"]))
    with threadpool_limits(limits=int(config["threads"])):
        for row_index in warmup_indices:
            model.predict_proba(inputs[row_index : row_index + 1])

    individual_rows = []
    for repetition in range(int(config["repetitions"])):
        indices = rng.integers(
            0, len(inputs), size=int(config["individual_calls_per_repetition"])
        )
        with threadpool_limits(limits=int(config["threads"])):
            for call_id, row_index in enumerate(indices):
                start_ns = time.perf_counter_ns()
                probabilities = model.predict_proba(inputs[row_index : row_index + 1])
                duration_ns = time.perf_counter_ns() - start_ns
                if probabilities.shape != (1, len(schema["class_order"])):
                    raise AssertionError("Unexpected individual prediction shape")
                individual_rows.append(
                    {
                        "model": model_name,
                        "repetition": repetition,
                        "call_id": call_id,
                        "row_id": int(row_index),
                        "duration_ns": duration_ns,
                    }
                )

    batch_rows = []
    for repetition in range(int(config["repetitions"])):
        for batch_size in config["batch_sizes"]:
            for call_id in range(int(config["batch_calls_per_repetition"])):
                indices = rng.integers(0, len(inputs), size=int(batch_size))
                batch = inputs[indices]
                with threadpool_limits(limits=int(config["threads"])):
                    start_ns = time.perf_counter_ns()
                    probabilities = model.predict_proba(batch)
                    duration_ns = time.perf_counter_ns() - start_ns
                if probabilities.shape != (batch_size, len(schema["class_order"])):
                    raise AssertionError("Unexpected batch prediction shape")
                batch_rows.append(
                    {
                        "model": model_name,
                        "repetition": repetition,
                        "batch_size": int(batch_size),
                        "call_id": call_id,
                        "duration_ns": duration_ns,
                        "amortized_ns_per_row": duration_ns / batch_size,
                        "rows_per_second": batch_size / (duration_ns / 1_000_000_000),
                    }
                )

    output_dir = project_root / "benchmarks" / config["benchmark_id"]
    output_dir.mkdir(parents=True, exist_ok=True)
    individual = pd.DataFrame(individual_rows)
    batches = pd.DataFrame(batch_rows)
    individual_path = output_dir / f"{model_name}__individual.csv.gz"
    batch_path = output_dir / f"{model_name}__batch.csv.gz"
    write_gzip_csv(individual_path, individual)
    write_gzip_csv(batch_path, batches)

    batch_summary = []
    for batch_size, selected in batches.groupby("batch_size"):
        row_summary = distribution_summary(selected["duration_ns"].to_numpy())
        row_summary.update(
            {
                "batch_size": int(batch_size),
                "amortized_p50_us_per_row": float(
                    np.quantile(selected["amortized_ns_per_row"] / 1_000, 0.50)
                ),
                "median_rows_per_second": float(
                    np.median(selected["rows_per_second"])
                ),
            }
        )
        batch_summary.append(row_summary)
    summary = {
        "benchmark_id": config["benchmark_id"],
        "config_sha256": json_hash(config),
        "model": model_name,
        "model_sha256": model_record["sha256"],
        "model_bytes": model_record["bytes"],
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "threads": config["threads"],
        "warmup_calls": config["warmup_calls"],
        "repetitions": config["repetitions"],
        "load_seconds": load_seconds,
        "rss_before_load_bytes": rss_before_load,
        "rss_after_load_bytes": rss_after_load,
        "rss_load_delta_bytes": rss_after_load - rss_before_load,
        "individual": distribution_summary(individual["duration_ns"].to_numpy()),
        "batches": batch_summary,
        "individual_file": individual_path.name,
        "individual_sha256": file_hash(individual_path),
        "batch_file": batch_path.name,
        "batch_sha256": file_hash(batch_path),
        "environment": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "logical_cpu_count": psutil.cpu_count(logical=True),
            "physical_cpu_count": psutil.cpu_count(logical=False),
        },
    }
    write_json(output_dir / f"{model_name}__summary.json", summary)
    del model
    gc.collect()
    print(
        f"BENCHMARK {model_name} p50={summary['individual']['p50_us']:.2f}us "
        f"p99={summary['individual']['p99_us']:.2f}us"
    )
    return summary


def write_manifest(project_root: Path, config_path: Path) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    output_dir = project_root / "benchmarks" / config["benchmark_id"]
    summaries = []
    for model_name in config["models"]:
        path = output_dir / f"{model_name}__summary.json"
        if path.exists():
            summaries.append(json.loads(path.read_text(encoding="utf-8")))
    manifest = {
        "benchmark_id": config["benchmark_id"],
        "status": "pilot_local_in_process",
        "config_sha256": json_hash(config),
        "completed_models": len(summaries),
        "expected_models": len(config["models"]),
        "complete": len(summaries) == len(config["models"]),
        "models": [item["model"] for item in summaries],
        "model_summaries": [f"{item['model']}__summary.json" for item in summaries],
    }
    write_json(output_dir / "manifest.json", manifest)
    return manifest


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=project_root / "configs" / "local_benchmark_v1.json",
    )
    parser.add_argument("--model", choices=["xgboost", "random_forest"])
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    models = [args.model] if args.model else config["models"]
    for model_name in models:
        benchmark_model(project_root, config_path, model_name)
    manifest = write_manifest(project_root, config_path)
    print(f"Benchmark models: {manifest['completed_models']}/{manifest['expected_models']}")


if __name__ == "__main__":
    main()
