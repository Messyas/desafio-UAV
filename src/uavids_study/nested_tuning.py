"""Nested, group-aware hyperparameter selection for UAVIDS-2025."""

from __future__ import annotations

import argparse
import json
import pickle
import sys
import time
import traceback
import warnings
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold
from threadpoolctl import threadpool_limits

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from uavids_study.predictive_experiment import (  # type: ignore
        _iteration_count,
        _prediction_frame,
        build_estimator,
        file_hash,
        json_hash,
        predictive_metrics,
        write_aggregates,
        write_gzip_csv,
        write_json,
    )
else:
    from .predictive_experiment import (
        _iteration_count,
        _prediction_frame,
        build_estimator,
        file_hash,
        json_hash,
        predictive_metrics,
        write_aggregates,
        write_gzip_csv,
        write_json,
    )


TARGET_COLUMN = "label"


def make_inner_splits(
    splits: pd.DataFrame,
    y: np.ndarray,
    outer_train_rows: np.ndarray,
    protocol: str,
    *,
    n_splits: int,
    seed: int,
) -> list[tuple[np.ndarray, np.ndarray]]:
    """Return positions relative to outer_train_rows, never global row ids."""

    outer_splits = splits.iloc[outer_train_rows]
    outer_y = y[outer_train_rows]
    dummy = np.zeros((len(outer_train_rows), 1), dtype=np.uint8)
    if protocol == "S0":
        splitter = StratifiedKFold(
            n_splits=n_splits, shuffle=True, random_state=seed
        )
        generated = splitter.split(dummy, outer_y)
        group_values = None
    elif protocol in {"S1", "S2"}:
        group_column = f"{protocol.lower()}_group"
        group_values = outer_splits[group_column].to_numpy()
        splitter = StratifiedGroupKFold(
            n_splits=n_splits, shuffle=True, random_state=seed
        )
        generated = splitter.split(dummy, outer_y, groups=group_values)
    else:
        raise ValueError(f"Unsupported protocol: {protocol}")

    folds = []
    all_classes = set(np.unique(outer_y))
    for inner_train, inner_validation in generated:
        if set(inner_train).intersection(inner_validation):
            raise AssertionError("Inner train and validation positions overlap")
        if set(np.unique(outer_y[inner_train])) != all_classes:
            raise AssertionError("An inner training fold is missing a class")
        if set(np.unique(outer_y[inner_validation])) != all_classes:
            raise AssertionError("An inner validation fold is missing a class")
        if group_values is not None:
            train_groups = set(group_values[inner_train])
            validation_groups = set(group_values[inner_validation])
            if not train_groups.isdisjoint(validation_groups):
                raise AssertionError("A group crosses inner train and validation")
        folds.append((inner_train, inner_validation))
    return folds


def select_candidate(
    candidate_results: list[dict[str, Any]], tie_tolerance: float
) -> dict[str, Any]:
    best_score = max(item["mean_inner_f1_macro"] for item in candidate_results)
    eligible = [
        item
        for item in candidate_results
        if item["mean_inner_f1_macro"] >= best_score - tie_tolerance
    ]
    return min(
        eligible,
        key=lambda item: (item["complexity_rank"], item["candidate_id"]),
    )


def run_nested_job(
    data: pd.DataFrame,
    splits: pd.DataFrame,
    config: dict[str, Any],
    config_sha256: str,
    output_dir: Path,
    *,
    protocol: str,
    outer_fold: int,
    model_name: str,
    force: bool = False,
) -> dict[str, Any]:
    seed = int(config["random_seed"])
    threads = int(config["threads"])
    model_config = config["models"][model_name]
    job_id = f"{protocol.lower()}__fold_{outer_fold}__{model_name}__seed_{seed}"
    record_path = output_dir / "job_records" / f"{job_id}.json"
    prediction_path = output_dir / "job_predictions" / f"{job_id}.csv.gz"
    if not force and record_path.exists() and prediction_path.exists():
        record = json.loads(record_path.read_text(encoding="utf-8"))
        if (
            record.get("status") == "complete"
            and record.get("config_sha256") == config_sha256
            and record.get("prediction_sha256") == file_hash(prediction_path)
        ):
            print(f"SKIP {job_id}", flush=True)
            return record

    print(f"RUN  {job_id}", flush=True)
    class_order = list(config["class_order"])
    class_to_id = {name: index for index, name in enumerate(class_order)}
    y_series = data[TARGET_COLUMN].map(class_to_id)
    if y_series.isna().any():
        raise ValueError("Dataset contains a label outside class_order")
    y = y_series.to_numpy(dtype=np.int8)
    features = list(config["primary_features"])
    outer_fold_values = splits[f"{protocol.lower()}_fold"].to_numpy()
    outer_test_rows = np.flatnonzero(outer_fold_values == outer_fold)
    outer_train_rows = np.flatnonzero(outer_fold_values != outer_fold)
    inner_splits = make_inner_splits(
        splits,
        y,
        outer_train_rows,
        protocol,
        n_splits=int(config["inner_folds"]),
        seed=seed + outer_fold,
    )

    candidate_results = []
    tuning_warnings = []
    tuning_start = time.perf_counter()
    for candidate in model_config["candidates"]:
        inner_scores = []
        inner_fit_seconds = []
        for inner_fold, (inner_train_positions, inner_validation_positions) in enumerate(
            inner_splits
        ):
            train_rows = outer_train_rows[inner_train_positions]
            validation_rows = outer_train_rows[inner_validation_positions]
            candidate_config = {
                "scale": model_config.get("scale", False),
                "parameters": candidate["parameters"],
            }
            estimator = build_estimator(
                model_name,
                candidate_config,
                seed=seed + outer_fold * 100 + inner_fold,
                threads=threads,
            )
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                with threadpool_limits(limits=threads):
                    start = time.perf_counter()
                    estimator.fit(
                        data.iloc[train_rows][features],
                        y[train_rows],
                    )
                    inner_fit_seconds.append(time.perf_counter() - start)
                    probabilities = estimator.predict_proba(
                        data.iloc[validation_rows][features]
                    )
            if not np.array_equal(
                estimator.named_steps["model"].classes_, np.arange(len(class_order))
            ):
                raise AssertionError("Estimator class order changed in inner CV")
            predictions = probabilities.argmax(axis=1)
            score = f1_score(
                y[validation_rows],
                predictions,
                labels=np.arange(len(class_order)),
                average="macro",
                zero_division=0,
            )
            inner_scores.append(float(score))
            tuning_warnings.extend(
                {
                    "candidate_id": candidate["candidate_id"],
                    "inner_fold": inner_fold,
                    "category": item.category.__name__,
                    "message": str(item.message),
                }
                for item in caught
            )
        candidate_results.append(
            {
                "candidate_id": candidate["candidate_id"],
                "complexity_rank": candidate["complexity_rank"],
                "parameters": candidate["parameters"],
                "inner_f1_macro": inner_scores,
                "mean_inner_f1_macro": float(np.mean(inner_scores)),
                "std_inner_f1_macro": float(np.std(inner_scores, ddof=1)),
                "inner_fit_seconds": inner_fit_seconds,
                "total_inner_fit_seconds": float(sum(inner_fit_seconds)),
            }
        )
    tuning_seconds = time.perf_counter() - tuning_start
    selected = select_candidate(candidate_results, float(config["tie_tolerance"]))

    final_config = {
        "scale": model_config.get("scale", False),
        "parameters": selected["parameters"],
    }
    final_estimator = build_estimator(
        model_name,
        final_config,
        seed=seed + outer_fold * 1000,
        threads=threads,
    )
    with warnings.catch_warnings(record=True) as final_warnings:
        warnings.simplefilter("always")
        with threadpool_limits(limits=threads):
            start = time.perf_counter()
            final_estimator.fit(
                data.iloc[outer_train_rows][features], y[outer_train_rows]
            )
            fit_seconds = time.perf_counter() - start
            start = time.perf_counter()
            probabilities = final_estimator.predict_proba(
                data.iloc[outer_test_rows][features]
            )
            inference_seconds = time.perf_counter() - start
    if not np.array_equal(
        final_estimator.named_steps["model"].classes_, np.arange(len(class_order))
    ):
        raise AssertionError("Estimator class order changed in external fit")
    predictions = probabilities.argmax(axis=1).astype(np.int8)
    metrics, class_metrics, confusion_rows = predictive_metrics(
        y[outer_test_rows], predictions, probabilities, class_order
    )
    prediction_frame = _prediction_frame(
        splits.iloc[outer_test_rows],
        y[outer_test_rows],
        predictions,
        probabilities,
        class_order,
        protocol=protocol,
        fold=outer_fold,
        model_name=model_name,
        seed=seed,
    )
    write_gzip_csv(prediction_path, prediction_frame)
    all_warnings = tuning_warnings + [
        {
            "candidate_id": selected["candidate_id"],
            "inner_fold": None,
            "category": item.category.__name__,
            "message": str(item.message),
        }
        for item in final_warnings
    ]
    record = {
        "job_id": job_id,
        "status": "complete",
        "config_sha256": config_sha256,
        "protocol": protocol,
        "fold": outer_fold,
        "model": model_name,
        "diagnostic_only": False,
        "seed": seed,
        "features": features,
        "train_rows": int(len(outer_train_rows)),
        "test_rows": int(len(outer_test_rows)),
        "inner_folds": int(config["inner_folds"]),
        "candidate_results": candidate_results,
        "selected_candidate_id": selected["candidate_id"],
        "selected_parameters": selected["parameters"],
        "inner_selection_score": selected["mean_inner_f1_macro"],
        "tuning_fit_count": len(candidate_results) * len(inner_splits),
        "total_fit_count": len(candidate_results) * len(inner_splits) + 1,
        "tuning_seconds": tuning_seconds,
        "fit_seconds": fit_seconds,
        "inference_seconds": inference_seconds,
        "inference_microseconds_per_row_amortized": (
            inference_seconds / len(outer_test_rows) * 1_000_000
        ),
        "serialized_model_bytes": len(
            pickle.dumps(final_estimator, protocol=pickle.HIGHEST_PROTOCOL)
        ),
        "iteration_count": _iteration_count(final_estimator),
        "warnings": all_warnings,
        "metrics": metrics,
        "class_metrics": class_metrics,
        "confusion": confusion_rows,
        "prediction_file": prediction_path.relative_to(output_dir).as_posix(),
        "prediction_sha256": file_hash(prediction_path),
    }
    write_json(record_path, record)
    print(
        f"DONE {job_id} selected={selected['candidate_id']} "
        f"inner={selected['mean_inner_f1_macro']:.6f} "
        f"outer={metrics['f1_macro']:.6f}",
        flush=True,
    )
    return record


def run_nested_experiment(
    project_root: Path,
    config_path: Path,
    *,
    selected_folds: list[int] | None = None,
    selected_models: list[str] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    config = json.loads(config_path.read_text(encoding="utf-8"))
    config_sha256 = json_hash(config)
    dataset_path = project_root / "notebooks" / "data" / "raw" / "UAVIDS-2025.csv"
    split_path = project_root / "research_artifacts" / "data_audit" / "split_candidates.csv.gz"
    output_dir = project_root / "results" / config["experiment_id"]
    output_dir.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(dataset_path)
    splits = pd.read_csv(split_path)
    if len(data) != len(splits):
        raise AssertionError("Dataset and split manifest have different row counts")
    if not np.array_equal(splits["flow_id"].to_numpy(), data["FlowID"].to_numpy()):
        raise AssertionError("Split manifest no longer matches dataset order")

    folds = selected_folds or list(config["folds"])
    models = selected_models or [
        name for name, value in config["models"].items() if value.get("enabled", False)
    ]
    failures = []
    for protocol in config["protocols"]:
        for outer_fold in folds:
            for model_name in models:
                try:
                    run_nested_job(
                        data,
                        splits,
                        config,
                        config_sha256,
                        output_dir,
                        protocol=protocol,
                        outer_fold=outer_fold,
                        model_name=model_name,
                        force=force,
                    )
                except Exception as exc:
                    failure = {
                        "protocol": protocol,
                        "fold": outer_fold,
                        "model": model_name,
                        "error_type": type(exc).__name__,
                        "error": str(exc),
                        "traceback": traceback.format_exc(),
                    }
                    failures.append(failure)
                    write_json(
                        output_dir
                        / "job_records"
                        / f"{protocol.lower()}__fold_{outer_fold}__{model_name}__failed.json",
                        failure,
                    )
                    print(
                        f"FAIL {protocol} fold={outer_fold} model={model_name}: {exc}",
                        file=sys.stderr,
                    )
    manifest = write_aggregates(
        output_dir, config, config_sha256, dataset_path, split_path
    )
    if failures:
        raise RuntimeError(f"{len(failures)} nested jobs failed")
    print(
        f"Nested experiment jobs: {manifest['completed_jobs']}/{manifest['expected_jobs']}",
        flush=True,
    )
    return manifest


def _comma_list(value: str | None, cast=str) -> list[Any] | None:
    if value is None:
        return None
    return [cast(item.strip()) for item in value.split(",") if item.strip()]


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=project_root / "configs" / "nested_tuning_v2.json",
    )
    parser.add_argument("--folds", help="Comma-separated external folds")
    parser.add_argument("--models", help="Comma-separated models")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run_nested_experiment(
        project_root,
        args.config.resolve(),
        selected_folds=_comma_list(args.folds, int),
        selected_models=_comma_list(args.models, str),
        force=args.force,
    )


if __name__ == "__main__":
    main()
