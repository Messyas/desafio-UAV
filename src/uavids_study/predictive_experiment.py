"""Leakage-aware, resumable baseline evaluation for UAVIDS-2025."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import pickle
import platform
import sys
import time
import traceback
import warnings
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import ExtraTreesClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    log_loss,
    precision_recall_fscore_support,
)
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits


TARGET_COLUMN = "label"


def file_hash(path: Path, algorithm: str = "sha256") -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def json_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, Path):
        return value.as_posix()
    raise TypeError(f"Cannot serialize {type(value)!r}")


def write_gzip_csv(path: Path, frame: pd.DataFrame) -> None:
    """Write deterministic gzip output so its checksum can be registered."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw_stream:
        with gzip.GzipFile(
            filename="predictions.csv",
            mode="wb",
            fileobj=raw_stream,
            mtime=0,
        ) as gzip_stream:
            frame.to_csv(gzip_stream, index=False, lineterminator="\n")


def build_estimator(
    model_name: str,
    model_config: dict[str, Any],
    *,
    seed: int,
    threads: int,
) -> Pipeline:
    """Create a fresh estimator; preprocessing remains inside the fold pipeline."""

    parameters = dict(model_config.get("parameters", {}))
    if model_name == "dummy_prior":
        estimator = DummyClassifier(**parameters)
    elif model_name == "logistic_regression":
        estimator = LogisticRegression(random_state=seed, **parameters)
    elif model_name in {"random_forest", "random_forest_with_flow_id"}:
        estimator = RandomForestClassifier(
            random_state=seed, n_jobs=threads, **parameters
        )
    elif model_name == "extra_trees":
        estimator = ExtraTreesClassifier(
            random_state=seed, n_jobs=threads, **parameters
        )
    elif model_name == "xgboost":
        try:
            from xgboost import XGBClassifier
        except ImportError as exc:
            raise RuntimeError("xgboost is enabled but not installed") from exc
        estimator = XGBClassifier(
            random_state=seed,
            n_jobs=threads,
            verbosity=0,
            **parameters,
        )
    elif model_name == "mlp_compact":
        if isinstance(parameters.get("hidden_layer_sizes"), list):
            parameters["hidden_layer_sizes"] = tuple(parameters["hidden_layer_sizes"])
        estimator = MLPClassifier(random_state=seed, **parameters)
    else:
        raise ValueError(f"Unknown model: {model_name}")

    steps = []
    if model_config.get("scale", False):
        steps.append(("scaler", StandardScaler()))
    steps.append(("model", estimator))
    return Pipeline(steps)


def predictive_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    probabilities: np.ndarray,
    class_order: list[str],
) -> tuple[dict[str, float], list[dict[str, Any]], list[dict[str, Any]]]:
    """Calculate fixed-label metrics separately from estimator fitting."""

    labels = np.arange(len(class_order))
    precision, recall, f1, support = precision_recall_fscore_support(
        y_true, y_pred, labels=labels, zero_division=0
    )
    normal_class = 0
    normal_mask = y_true == normal_class
    attack_mask = ~normal_mask
    metrics = {
        "rows": int(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "f1_macro": float(f1.mean()),
        "log_loss": float(log_loss(y_true, probabilities, labels=labels)),
        "false_alarm_rate": float((y_pred[normal_mask] != normal_class).mean()),
        "missed_attack_rate": float((y_pred[attack_mask] == normal_class).mean()),
    }
    class_metrics = []
    for class_id, class_name in enumerate(class_order):
        class_metrics.append(
            {
                "class_id": class_id,
                "class_name": class_name,
                "precision": float(precision[class_id]),
                "recall": float(recall[class_id]),
                "f1": float(f1[class_id]),
                "support": int(support[class_id]),
            }
        )
    matrix = confusion_matrix(y_true, y_pred, labels=labels)
    confusion_rows = []
    for true_id, true_name in enumerate(class_order):
        for predicted_id, predicted_name in enumerate(class_order):
            confusion_rows.append(
                {
                    "true_class_id": true_id,
                    "true_class": true_name,
                    "predicted_class_id": predicted_id,
                    "predicted_class": predicted_name,
                    "rows": int(matrix[true_id, predicted_id]),
                }
            )
    return metrics, class_metrics, confusion_rows


def _iteration_count(pipeline: Pipeline) -> int | list[int] | None:
    estimator = pipeline.named_steps["model"]
    value = getattr(estimator, "n_iter_", None)
    if value is None:
        return None
    array = np.asarray(value).reshape(-1)
    values = [int(item) for item in array]
    return values[0] if len(values) == 1 else values


def _prediction_frame(
    split_rows: pd.DataFrame,
    y_true: np.ndarray,
    y_pred: np.ndarray,
    probabilities: np.ndarray,
    class_order: list[str],
    *,
    protocol: str,
    fold: int,
    model_name: str,
    seed: int,
) -> pd.DataFrame:
    output = pd.DataFrame(
        {
            "row_id": split_rows["row_id"].to_numpy(),
            "flow_id": split_rows["flow_id"].to_numpy(),
            "protocol": protocol,
            "fold": fold,
            "model": model_name,
            "seed": seed,
            "y_true": [class_order[item] for item in y_true],
            "y_pred": [class_order[item] for item in y_pred],
        }
    )
    for class_id, class_name in enumerate(class_order):
        safe_name = class_name.lower().replace(" ", "_")
        output[f"probability__{safe_name}"] = probabilities[:, class_id]
    return output


def run_job(
    data: pd.DataFrame,
    splits: pd.DataFrame,
    config: dict[str, Any],
    config_sha256: str,
    output_dir: Path,
    *,
    protocol: str,
    fold: int,
    model_name: str,
    seed_override: int | None = None,
    force: bool = False,
) -> dict[str, Any]:
    seed = int(config["random_seed"] if seed_override is None else seed_override)
    threads = int(config["threads"])
    model_config = config["models"][model_name]
    job_id = f"{protocol.lower()}__fold_{fold}__{model_name}__seed_{seed}"
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
    fold_column = f"{protocol.lower()}_fold"
    test_mask = splits[fold_column].to_numpy() == fold
    train_mask = ~test_mask
    train_rows = np.flatnonzero(train_mask)
    test_rows = np.flatnonzero(test_mask)

    features = list(config["primary_features"])
    features.extend(model_config.get("additional_features", []))
    class_order = list(config["class_order"])
    class_to_id = {class_name: class_id for class_id, class_name in enumerate(class_order)}
    y = data[TARGET_COLUMN].map(class_to_id)
    if y.isna().any():
        unknown = sorted(data.loc[y.isna(), TARGET_COLUMN].astype(str).unique())
        raise ValueError(f"Labels absent from class_order: {unknown}")

    x_train = data.iloc[train_rows][features]
    x_test = data.iloc[test_rows][features]
    y_train = y.iloc[train_rows].to_numpy(dtype=np.int8)
    y_test = y.iloc[test_rows].to_numpy(dtype=np.int8)
    estimator = build_estimator(
        model_name, model_config, seed=seed, threads=threads
    )

    caught_warnings: list[warnings.WarningMessage]
    with warnings.catch_warnings(record=True) as caught_warnings:
        warnings.simplefilter("always")
        with threadpool_limits(limits=threads):
            fit_start = time.perf_counter()
            estimator.fit(x_train, y_train)
            fit_seconds = time.perf_counter() - fit_start
            inference_start = time.perf_counter()
            probabilities = estimator.predict_proba(x_test)
            inference_seconds = time.perf_counter() - inference_start

    estimator_classes = estimator.named_steps["model"].classes_
    expected_classes = np.arange(len(class_order))
    if not np.array_equal(estimator_classes, expected_classes):
        raise AssertionError(
            f"Estimator class order {estimator_classes} differs from {expected_classes}"
        )
    y_pred = probabilities.argmax(axis=1).astype(np.int8)
    metrics, class_metrics, confusion_rows = predictive_metrics(
        y_test, y_pred, probabilities, class_order
    )
    serialized_size = len(pickle.dumps(estimator, protocol=pickle.HIGHEST_PROTOCOL))
    predictions = _prediction_frame(
        splits.iloc[test_rows],
        y_test,
        y_pred,
        probabilities,
        class_order,
        protocol=protocol,
        fold=fold,
        model_name=model_name,
        seed=seed,
    )
    write_gzip_csv(prediction_path, predictions)

    record = {
        "job_id": job_id,
        "status": "complete",
        "config_sha256": config_sha256,
        "protocol": protocol,
        "fold": fold,
        "model": model_name,
        "diagnostic_only": bool(model_config.get("diagnostic_only", False)),
        "seed": seed,
        "features": features,
        "train_rows": int(train_mask.sum()),
        "test_rows": int(test_mask.sum()),
        "fit_seconds": fit_seconds,
        "inference_seconds": inference_seconds,
        "inference_microseconds_per_row_amortized": (
            inference_seconds / len(test_rows) * 1_000_000
        ),
        "serialized_model_bytes": serialized_size,
        "iteration_count": _iteration_count(estimator),
        "warnings": [
            {
                "category": item.category.__name__,
                "message": str(item.message),
            }
            for item in caught_warnings
        ],
        "metrics": metrics,
        "class_metrics": class_metrics,
        "confusion": confusion_rows,
        "prediction_file": prediction_path.relative_to(output_dir).as_posix(),
        "prediction_sha256": file_hash(prediction_path),
    }
    write_json(record_path, record)
    print(
        f"DONE {job_id} f1_macro={metrics['f1_macro']:.6f} "
        f"fit={fit_seconds:.2f}s",
        flush=True,
    )
    return record


def write_aggregates(
    output_dir: Path,
    config: dict[str, Any],
    config_sha256: str,
    dataset_path: Path,
    split_path: Path,
) -> dict[str, Any]:
    records = []
    for path in sorted((output_dir / "job_records").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("config_sha256") == config_sha256:
            records.append(record)

    metric_rows = []
    class_rows = []
    confusion_rows = []
    for record in records:
        base = {
            "protocol": record["protocol"],
            "fold": record["fold"],
            "model": record["model"],
            "diagnostic_only": record["diagnostic_only"],
            "seed": record["seed"],
        }
        metric_rows.append(
            {
                **base,
                **record["metrics"],
                "fit_seconds": record["fit_seconds"],
                "inference_seconds": record["inference_seconds"],
                "inference_microseconds_per_row_amortized": record[
                    "inference_microseconds_per_row_amortized"
                ],
                "serialized_model_bytes": record["serialized_model_bytes"],
                "warning_count": len(record["warnings"]),
            }
        )
        class_rows.extend({**base, **row} for row in record["class_metrics"])
        confusion_rows.extend({**base, **row} for row in record["confusion"])

    metrics = pd.DataFrame(metric_rows)
    class_metrics = pd.DataFrame(class_rows)
    confusions = pd.DataFrame(confusion_rows)
    if not metrics.empty:
        metrics = metrics.sort_values(["protocol", "model", "fold", "seed"])
        metrics.to_csv(output_dir / "metrics_by_fold.csv", index=False, lineterminator="\n")
        class_metrics.to_csv(
            output_dir / "class_metrics_by_fold.csv", index=False, lineterminator="\n"
        )
        confusions["true_class_fraction"] = confusions["rows"] / confusions.groupby(
            ["protocol", "fold", "model", "seed", "true_class_id"]
        )["rows"].transform("sum")
        confusions.to_csv(
            output_dir / "confusion_matrices.csv", index=False, lineterminator="\n"
        )
        value_columns = [
            "accuracy",
            "balanced_accuracy",
            "f1_macro",
            "log_loss",
            "false_alarm_rate",
            "missed_attack_rate",
            "fit_seconds",
            "inference_microseconds_per_row_amortized",
            "serialized_model_bytes",
        ]
        summary = (
            metrics.groupby(["protocol", "model", "diagnostic_only"])[value_columns]
            .agg(["mean", "std", "min", "max"])
        )
        summary.columns = [f"{name}__{stat}" for name, stat in summary.columns]
        summary.reset_index().to_csv(
            output_dir / "metrics_summary.csv", index=False, lineterminator="\n"
        )

        pooled_metric_rows = []
        pooled_class_rows = []
        pooled_confusion_rows = []
        class_order = list(config["class_order"])
        class_to_id = {
            class_name: class_id for class_id, class_name in enumerate(class_order)
        }
        dataset_rows = sum(1 for _ in dataset_path.open("r", encoding="utf-8")) - 1
        for (protocol, model, seed), group_records in pd.DataFrame(records).groupby(
            ["protocol", "model", "seed"], sort=True
        ):
            prediction_frames = [
                pd.read_csv(output_dir / relative_path)
                for relative_path in group_records["prediction_file"]
            ]
            pooled = pd.concat(prediction_frames, ignore_index=True)
            if len(group_records) == len(config["folds"]):
                if len(pooled) != dataset_rows or not pooled["row_id"].is_unique:
                    raise AssertionError(
                        f"Incomplete or duplicated OOF population for {protocol}/{model}"
                    )
            y_true = pooled["y_true"].map(class_to_id).to_numpy(dtype=np.int8)
            y_pred = pooled["y_pred"].map(class_to_id).to_numpy(dtype=np.int8)
            probability_columns = [
                f"probability__{name.lower().replace(' ', '_')}"
                for name in class_order
            ]
            probabilities = pooled[probability_columns].to_numpy(dtype=np.float64)
            probability_sums = probabilities.sum(axis=1, keepdims=True)
            probabilities = np.divide(
                probabilities,
                probability_sums,
                out=np.zeros_like(probabilities),
                where=probability_sums != 0,
            )
            pooled_metrics, pooled_classes, pooled_confusion = predictive_metrics(
                y_true, y_pred, probabilities, class_order
            )
            diagnostic_only = bool(group_records["diagnostic_only"].iloc[0])
            base = {
                "protocol": protocol,
                "model": model,
                "seed": int(seed),
                "diagnostic_only": diagnostic_only,
                "folds_combined": int(len(group_records)),
            }
            pooled_metric_rows.append({**base, **pooled_metrics})
            pooled_class_rows.extend({**base, **row} for row in pooled_classes)
            pooled_confusion_rows.extend({**base, **row} for row in pooled_confusion)

        pd.DataFrame(pooled_metric_rows).to_csv(
            output_dir / "metrics_pooled_oof.csv", index=False, lineterminator="\n"
        )
        pd.DataFrame(pooled_class_rows).to_csv(
            output_dir / "class_metrics_pooled_oof.csv", index=False, lineterminator="\n"
        )
        pooled_confusions = pd.DataFrame(pooled_confusion_rows)
        pooled_confusions["true_class_fraction"] = pooled_confusions[
            "rows"
        ] / pooled_confusions.groupby(
            ["protocol", "model", "true_class_id"]
        )["rows"].transform("sum")
        pooled_confusions.to_csv(
            output_dir / "confusion_pooled_oof.csv", index=False, lineterminator="\n"
        )

    enabled_models = [
        name for name, value in config["models"].items() if value.get("enabled", False)
    ]
    configured_seeds = config.get("random_seeds", [config["random_seed"]])
    expected_jobs = (
        len(config["protocols"])
        * len(config["folds"])
        * len(enabled_models)
        * len(configured_seeds)
    )
    manifest = {
        "experiment_id": config["experiment_id"],
        "status": config["status"],
        "config_sha256": config_sha256,
        "dataset_sha256": file_hash(dataset_path),
        "split_sha256": file_hash(split_path),
        "completed_jobs": len(records),
        "expected_jobs": expected_jobs,
        "complete": len(records) == expected_jobs,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scikit_learn": sklearn.__version__,
            "xgboost": version("xgboost"),
            "processor": platform.processor() or "not_reported_by_platform",
            "logical_cpu_count": os.cpu_count(),
            "threads_allowed_per_fit": config["threads"],
            "accelerator": "none_used",
        },
        "class_order": config["class_order"],
        "prediction_schema": [
            "row_id",
            "flow_id",
            "protocol",
            "fold",
            "model",
            "seed",
            "y_true",
            "y_pred",
            *[
                f"probability__{name.lower().replace(' ', '_')}"
                for name in config["class_order"]
            ],
        ],
    }
    write_json(output_dir / "experiment_manifest.json", manifest)
    return manifest


def run_experiment(
    project_root: Path,
    config_path: Path,
    *,
    selected_protocols: list[str] | None = None,
    selected_folds: list[int] | None = None,
    selected_models: list[str] | None = None,
    selected_seeds: list[int] | None = None,
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
    if not np.array_equal(splits["row_id"].to_numpy(), np.arange(len(data))):
        raise AssertionError("Split row_id no longer matches dataset order")
    if not np.array_equal(splits["flow_id"].to_numpy(), data["FlowID"].to_numpy()):
        raise AssertionError("Split flow_id no longer matches dataset order")

    protocols = selected_protocols or list(config["protocols"])
    folds = selected_folds or list(config["folds"])
    models = selected_models or [
        name for name, value in config["models"].items() if value.get("enabled", False)
    ]
    seeds = selected_seeds or list(config.get("random_seeds", [config["random_seed"]]))
    invalid_protocols = sorted(set(protocols) - set(config["protocols"]))
    invalid_folds = sorted(set(folds) - set(config["folds"]))
    invalid_models = sorted(set(models) - set(config["models"]))
    if invalid_protocols or invalid_folds or invalid_models:
        raise ValueError(
            f"Invalid selections: protocols={invalid_protocols}, "
            f"folds={invalid_folds}, models={invalid_models}"
        )

    failures = []
    for protocol in protocols:
        for fold in folds:
            for model_name in models:
                if not config["models"][model_name].get("enabled", False):
                    continue
                for seed in seeds:
                    try:
                        run_job(
                            data,
                            splits,
                            config,
                            config_sha256,
                            output_dir,
                            protocol=protocol,
                            fold=fold,
                            model_name=model_name,
                            seed_override=seed,
                            force=force,
                        )
                    except Exception as exc:  # preserve all failed jobs for inspection
                        failure = {
                            "protocol": protocol,
                            "fold": fold,
                            "model": model_name,
                            "seed": seed,
                            "error_type": type(exc).__name__,
                            "error": str(exc),
                            "traceback": traceback.format_exc(),
                        }
                        failures.append(failure)
                        write_json(
                            output_dir
                            / "job_records"
                            / f"{protocol.lower()}__fold_{fold}__{model_name}__seed_{seed}__failed.json",
                            failure,
                        )
                        print(
                            f"FAIL {protocol} fold={fold} model={model_name} seed={seed}: {exc}",
                            file=sys.stderr,
                            flush=True,
                        )

    manifest = write_aggregates(
        output_dir, config, config_sha256, dataset_path, split_path
    )
    if failures:
        raise RuntimeError(f"{len(failures)} requested jobs failed; inspect job_records")
    print(
        f"Experiment jobs: {manifest['completed_jobs']}/{manifest['expected_jobs']}",
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
        default=project_root / "configs" / "predictive_baseline_v1.json",
    )
    parser.add_argument("--protocols", help="Comma-separated subset, e.g. S0,S1")
    parser.add_argument("--folds", help="Comma-separated subset, e.g. 0,1")
    parser.add_argument("--models", help="Comma-separated subset")
    parser.add_argument("--seeds", help="Comma-separated subset")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    run_experiment(
        project_root,
        args.config.resolve(),
        selected_protocols=_comma_list(args.protocols, str),
        selected_folds=_comma_list(args.folds, int),
        selected_models=_comma_list(args.models, str),
        selected_seeds=_comma_list(args.seeds, int),
        force=args.force,
    )


if __name__ == "__main__":
    main()
