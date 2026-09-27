"""Compare completed ablation runs with different experiment IDs in two checkouts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def compare(reference: Path, candidate: Path, *, abs_tolerance: float = 1e-12) -> dict:
    ref = read_json(reference / "frozen_protocol.json")
    new = read_json(candidate / "frozen_protocol.json")
    ref_config = {key: value for key, value in ref["config"].items() if key != "experiment_id"}
    new_config = {key: value for key, value in new["config"].items() if key != "experiment_id"}
    if ref_config != new_config:
        raise ValueError("Experimental configurations differ beyond experiment_id")
    for key in ("dataset_sha256", "split_sha256", "environment"):
        if ref["identity"][key] != new["identity"][key]:
            raise ValueError(f"Frozen identity differs: {key}")
    code_binary_equal = ref["identity"]["code_sha256"] == new["identity"]["code_sha256"]
    code_comparison = {}
    for name, checksum in ref["identity"]["code_sha256"].items():
        if name not in new["identity"]["code_sha256"]:
            raise ValueError("Training source coverage differs")
        old_bytes = (reference.resolve().parents[1] / "src/uavids_study" / name).read_bytes()
        new_bytes = (candidate.resolve().parents[1] / "src/uavids_study" / name).read_bytes()
        if hashlib.sha256(old_bytes).hexdigest() != checksum or hashlib.sha256(new_bytes).hexdigest() != new["identity"]["code_sha256"][name]:
            raise ValueError(f"Source differs from frozen checksum: {name}")
        if old_bytes.replace(b"\r\n", b"\n") != new_bytes.replace(b"\r\n", b"\n"):
            raise ValueError(f"Training source differs beyond line endings: {name}")
        code_comparison[name] = "binary_equal" if old_bytes == new_bytes else "equal_after_CRLF_to_LF"
    ref_manifest = read_json(reference / "experiment_manifest.json")
    new_manifest = read_json(candidate / "experiment_manifest.json")
    if not ref_manifest["complete"] or not new_manifest["complete"]:
        raise ValueError("Both experiments must be complete")
    ref_jobs = {p.stem: read_json(p) for p in (reference / "job_records").glob("*.json")}
    new_jobs = {p.stem: read_json(p) for p in (candidate / "job_records").glob("*.json")}
    if not ref_jobs or ref_jobs.keys() != new_jobs.keys():
        raise ValueError("Job coverage differs")
    failures = []
    mismatch_details = []
    semantic_failures = []
    metric_failures = []
    max_numeric_delta = 0.0
    max_f1_delta = 0.0
    for job_id, old in ref_jobs.items():
        current = new_jobs[job_id]
        if old["prediction_sha256"] != current["prediction_sha256"]:
            failures.append(job_id)
            original = pd.read_csv(reference / old["prediction_file"])
            reproduced = pd.read_csv(candidate / current["prediction_file"])
            changed = {}
            job_max_numeric_delta = 0.0
            if original.shape != reproduced.shape or list(original.columns) != list(reproduced.columns):
                changed = {"schema": "different"}
            else:
                for column in original.columns:
                    a, b = original[column], reproduced[column]
                    if pd.api.types.is_numeric_dtype(a) and pd.api.types.is_numeric_dtype(b):
                        delta = np.abs(a.to_numpy() - b.to_numpy())
                        if delta.size:
                            job_max_numeric_delta = max(job_max_numeric_delta, float(np.nanmax(delta)))
                        unequal = ~np.isclose(a.to_numpy(), b.to_numpy(), rtol=0, atol=abs_tolerance, equal_nan=True)
                        if unequal.any():
                            changed[column] = {"rows_beyond_tolerance": int(unequal.sum()),
                                "max_abs_delta": float(np.nanmax(np.abs(a.to_numpy()[unequal] - b.to_numpy()[unequal])))}
                    else:
                        unequal = ~(a.eq(b) | (a.isna() & b.isna()))
                        if unequal.any():
                            changed[column] = {"unequal_rows": int(unequal.sum())}
            if changed:
                semantic_failures.append(job_id)
            max_numeric_delta = max(max_numeric_delta, job_max_numeric_delta)
            mismatch_details.append({"job_id": job_id, "max_abs_numeric_delta": job_max_numeric_delta,
                "changed_columns_beyond_tolerance": changed})
        f1_delta = abs(old["metrics"]["f1_macro"] - current["metrics"]["f1_macro"])
        max_f1_delta = max(max_f1_delta, f1_delta)
        if f1_delta > abs_tolerance:
            metric_failures.append(job_id)
    return {
        "reference_experiment": ref["config"]["experiment_id"],
        "candidate_experiment": new["config"]["experiment_id"],
        "jobs_compared": len(ref_jobs),
        "exact_prediction_hash_matches": len(ref_jobs) - len(failures),
        "prediction_hash_mismatches": failures,
        "semantic_mismatches_beyond_tolerance": semantic_failures,
        "absolute_numeric_tolerance": abs_tolerance,
        "max_abs_numeric_delta": max_numeric_delta,
        "mismatch_details": mismatch_details,
        "max_abs_fold_f1_macro_delta": max_f1_delta,
        "fold_f1_macro_mismatches_beyond_tolerance": metric_failures,
        "data_split_environment_match": True,
        "training_code_binary_equal": code_binary_equal,
        "training_code_comparison": code_comparison,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reference", type=Path)
    parser.add_argument("candidate", type=Path)
    parser.add_argument("--abs-tolerance", type=float, default=1e-12)
    args = parser.parse_args()
    if args.abs_tolerance < 0:
        parser.error("--abs-tolerance must be nonnegative")
    result = compare(args.reference, args.candidate, abs_tolerance=args.abs_tolerance)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["semantic_mismatches_beyond_tolerance"] or result["fold_f1_macro_mismatches_beyond_tolerance"]:
        raise SystemExit(1)
