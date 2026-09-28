"""Check actual paired request rows, quotas and coverage of attempted models."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from uavids_study.predictive_experiment import write_json
from build_latency_comparison import build


def verify(root: Path, config_path: Path) -> dict:
    config = json.loads(config_path.read_text("utf-8"))
    comparison = build(root, config_path)
    directory = root / "benchmarks" / config["benchmark_id"]
    manifest = json.loads((directory / "manifest.json").read_text("utf-8"))
    attempts = set(manifest["models"]) | {item["model"] for item in manifest["failures"]}
    if attempts != set(config["models"]):
        raise ValueError("Not all configured models have a measured result or failure")
    reference = None
    counts = {}
    for name in manifest["models"]:
        summary = json.loads((directory / f"{name}__summary.json").read_text("utf-8"))
        if summary["limits"]["nano_cpus"] != int(config["cpu_limit"] * 1e9):
            raise ValueError(f"CPU quota mismatch: {name}")
        if summary["limits"]["memory_bytes"] != 512 * 1024**2:
            raise ValueError(f"Memory quota mismatch: {name}")
        if summary["service_metadata"]["runtime_threads"] != config["model_threads"]:
            raise ValueError(f"Runtime parallelism mismatch: {name}")
        individual = pd.read_csv(directory / f"{name}__individual.csv.gz")
        batch = pd.read_csv(directory / f"{name}__batch.csv.gz")
        calls = pd.read_csv(directory / f"{name}__throughput_calls.csv.gz")
        if len(individual) != config["repetitions"] * config["individual_calls_per_repetition"]:
            raise ValueError(f"Incomplete individual calls: {name}")
        if len(batch) != config["repetitions"] * config["batch_calls_per_repetition"] * len(config["batch_sizes"]):
            raise ValueError(f"Incomplete batch calls: {name}")
        if len(calls) != config["repetitions"] * config["throughput_requests_per_repetition"] * len(config["throughput_concurrency"]):
            raise ValueError(f"Incomplete throughput calls: {name}")
        selected = individual[["repetition", "call_id", "row_id"]]
        if reference is None:
            reference = selected
        else:
            pd.testing.assert_frame_equal(reference, selected)
        if not (individual.client_duration_ns > 0).all():
            raise ValueError(f"Invalid measured durations: {name}")
        counts[name] = {"individual": len(individual), "batch": len(batch), "throughput": len(calls)}
    audit = {"benchmark_id": config["benchmark_id"], "all_models_attempted": True,
             "measured_models": manifest["models"], "failed_models": manifest["failures"],
             "paired_individual_inputs_identical": True, "counts": counts,
             "all_models_have_latency": bool((comparison.latency_status == "complete").all())}
    write_json(root / "reports" / config["benchmark_id"] / "measurement_checks.json", audit)
    return audit


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=root / "configs/docker_latency_v4.json")
    args = parser.parse_args()
    print(json.dumps(verify(root, args.config), indent=2))
