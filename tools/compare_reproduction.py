"""Compare completed ablation runs with different experiment IDs in two checkouts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def compare(reference: Path, candidate: Path) -> dict:
    ref = read_json(reference / "frozen_protocol.json")
    new = read_json(candidate / "frozen_protocol.json")
    ref_config = {key: value for key, value in ref["config"].items() if key != "experiment_id"}
    new_config = {key: value for key, value in new["config"].items() if key != "experiment_id"}
    if ref_config != new_config:
        raise ValueError("Experimental configurations differ beyond experiment_id")
    for key in ("dataset_sha256", "split_sha256", "code_sha256", "environment"):
        if ref["identity"][key] != new["identity"][key]:
            raise ValueError(f"Frozen identity differs: {key}")
    ref_manifest = read_json(reference / "experiment_manifest.json")
    new_manifest = read_json(candidate / "experiment_manifest.json")
    if not ref_manifest["complete"] or not new_manifest["complete"]:
        raise ValueError("Both experiments must be complete")
    ref_jobs = {p.stem: read_json(p) for p in (reference / "job_records").glob("*.json")}
    new_jobs = {p.stem: read_json(p) for p in (candidate / "job_records").glob("*.json")}
    if not ref_jobs or ref_jobs.keys() != new_jobs.keys():
        raise ValueError("Job coverage differs")
    failures = []
    max_f1_delta = 0.0
    for job_id, old in ref_jobs.items():
        current = new_jobs[job_id]
        if old["prediction_sha256"] != current["prediction_sha256"]:
            failures.append(job_id)
        max_f1_delta = max(max_f1_delta, abs(old["metrics"]["f1_macro"] - current["metrics"]["f1_macro"]))
    return {
        "reference_experiment": ref["config"]["experiment_id"],
        "candidate_experiment": new["config"]["experiment_id"],
        "jobs_compared": len(ref_jobs),
        "exact_prediction_hash_matches": len(ref_jobs) - len(failures),
        "prediction_hash_mismatches": failures,
        "max_abs_fold_f1_macro_delta": max_f1_delta,
        "identity_match": True,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    args = parser.parse_args()
    result = compare(args.reference, args.candidate)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["prediction_hash_mismatches"]:
        raise SystemExit(1)
