"""Paired, group-resampled uncertainty of fixed out-of-fold predictions."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_limits

try:
    from .feature_ablation import ROOT, aggregate, validate_partitions, verified_records
    from .predictive_experiment import file_hash, predictive_metrics, write_json
except ImportError:
    from feature_ablation import ROOT, aggregate, validate_partitions, verified_records
    from predictive_experiment import file_hash, predictive_metrics, write_json


def macro_f1(matrix):
    """Fixed-label F1, including zero for an absent class; accepts leading axes."""
    matrix = np.asarray(matrix, dtype=float)
    diagonal = np.diagonal(matrix, axis1=-2, axis2=-1)
    denominator = matrix.sum(axis=-1) + matrix.sum(axis=-2)
    return np.divide(2 * diagonal, denominator, out=np.zeros_like(diagonal),
        where=denominator != 0).mean(axis=-1)


def validated_probabilities(frame, labels):
    columns = ["probability__" + label.lower().replace(" ", "_") for label in labels]
    values = frame[columns].to_numpy(dtype=float)
    totals = values.sum(axis=1, keepdims=True)
    if not np.isfinite(values).all() or (values < 0).any() or (values > 1).any() or not np.allclose(totals, 1, rtol=0, atol=1e-6):
        raise ValueError("Invalid class probabilities")
    # Float32 model outputs read from CSV become float64. Normalize only their
    # accepted rounding residual before log-loss, preserving every prediction.
    return values / totals


def paired_bootstrap(y_true, predictions, groups, *, classes, replicates, confidence, seed):
    """Uniform resampling of whole groups, same draw for every condition/model.

    Predictions has shape (conditions, rows). Return per-condition draws and
    quantiles of each difference from its first (reference) condition.
    """
    y_true, predictions, groups = np.asarray(y_true), np.asarray(predictions), np.asarray(groups)
    if predictions.ndim != 2 or predictions.shape[1] != len(y_true) or len(groups) != len(y_true):
        raise ValueError("Unpaired prediction arrays")
    if replicates < 2 or not 0 < confidence < 1 or classes < 2:
        raise ValueError("Invalid bootstrap settings")
    if not len(y_true) or pd.isna(groups).any():
        raise ValueError("Empty data or missing group")
    if np.any(y_true < 0) or np.any(y_true >= classes) or np.any(predictions < 0) or np.any(predictions >= classes):
        raise ValueError("Unknown class id")
    _, inverse = np.unique(groups, return_inverse=True)
    n_groups = inverse.max() + 1
    if n_groups < 2:
        raise ValueError("At least two groups are required")
    counts = np.stack([np.bincount(inverse * classes * classes + y_true * classes + pred,
        minlength=n_groups * classes * classes).reshape(n_groups, classes * classes)
        for pred in predictions], axis=1)
    flattened = counts.reshape(n_groups, -1).astype(float)
    rng = np.random.default_rng(seed)
    draws = np.empty((replicates, len(predictions)))
    missing_class_draws = 0
    # Bound memory even when S1 has over 100,000 signature groups.
    batch_size = max(1, min(64, 16_000_000 // (8 * n_groups)))
    with threadpool_limits(limits=4):
        for start in range(0, replicates, batch_size):
            size = min(batch_size, replicates - start)
            weights = rng.multinomial(n_groups, np.full(n_groups, 1 / n_groups), size=size)
            matrices = (weights @ flattened).reshape(size, len(predictions), classes, classes)
            draws[start:start + size] = macro_f1(matrices)
            missing_class_draws += int((matrices[:, 0].sum(axis=-1) == 0).any(axis=-1).sum())
    alpha = (1 - confidence) / 2
    differences = draws - draws[:, :1]
    return {"groups": int(n_groups), "draws": draws,
        "difference_intervals": np.quantile(differences, [alpha, 1 - alpha], axis=0).T,
        "missing_class_draws": missing_class_draws}


def load_cell(output, records, *, protocol, model, seed, condition, config, data, splits):
    subset = [record for record in records if all(record[key] == value for key, value in
        dict(protocol=protocol, model=model, seed=seed, condition=condition).items())]
    if sorted(record["fold"] for record in subset) != sorted(config["folds"]):
        raise ValueError(f"Incomplete OOF coverage: {protocol}/{model}/{seed}/{condition}")
    frames = []
    for record in subset:
        frame = pd.read_csv(output / record["prediction_file"])
        expected = splits.loc[splits[protocol.lower() + "_fold"] == record["fold"], "row_id"].to_numpy()
        if not np.array_equal(np.sort(frame.row_id.to_numpy()), expected):
            raise ValueError("Predictions do not match the recorded test fold")
        for key, value in dict(protocol=protocol, model=model, seed=seed, fold=record["fold"]).items():
            if not (frame[key] == value).all():
                raise ValueError(f"Prediction metadata mismatch: {key}")
        if not (frame["condition"] == condition).all():
            raise ValueError("Prediction condition mismatch")
        labels = config["class_order"]
        mapping = dict(zip(labels, range(len(labels))))
        measured, _, _ = predictive_metrics(frame.y_true.map(mapping).to_numpy(dtype=int),
            frame.y_pred.map(mapping).to_numpy(dtype=int), validated_probabilities(frame, labels), labels)
        if any(not math.isclose(value, record["metrics"][key], rel_tol=1e-6, abs_tol=1e-8)
            for key, value in measured.items()):
            raise ValueError("Recorded metrics differ from predictions")
        frames.append(frame)
    frame = pd.concat(frames).sort_values("row_id").reset_index(drop=True)
    if not np.array_equal(frame.row_id, np.arange(len(data))):
        raise ValueError("OOF rows must cover the dataset exactly once")
    if not np.array_equal(frame.flow_id, data.FlowID) or not np.array_equal(frame.y_true, data.label):
        raise ValueError("Prediction identity or ground truth mismatch")
    labels = config["class_order"]
    probabilities = validated_probabilities(frame, labels)
    predicted = frame.y_pred.map(dict(zip(labels, range(len(labels)))))
    if predicted.isna().any() or not np.array_equal(predicted, probabilities.argmax(axis=1)):
        raise ValueError("Predicted labels disagree with probabilities")
    return frame


def analyze(config_path, *, protocols=None):
    config = json.loads(Path(config_path).read_text("utf-8"))
    protocols = config["protocols"] if protocols is None else protocols
    if not protocols or set(protocols) - set(config["protocols"]):
        raise ValueError("Unknown or empty analysis protocols")
    output = ROOT / "results" / config["experiment_id"]
    frozen = json.loads((output / "frozen_protocol.json").read_text("utf-8"))
    data_path = ROOT / config.get("dataset_path", "notebooks/data/raw/UAVIDS-2025.csv")
    split_path = ROOT / config.get("split_path", "research_artifacts/data_audit/split_candidates.csv.gz")
    for key, path in (("dataset_sha256", data_path), ("split_sha256", split_path)):
        if file_hash(path) != frozen["identity"][key]:
            raise ValueError("Analysis data differ from training identity")
    data, splits = pd.read_csv(data_path), pd.read_csv(split_path)
    validate_partitions(data, splits, config)
    manifest = aggregate(output, config)
    records = verified_records(output, config)
    labels, options = config["class_order"], config["analysis"]
    mapping = dict(zip(labels, range(len(labels))))
    y = data.label.map(mapping).to_numpy(dtype=int)
    pooled_rows, class_rows, confusion_rows, comparison_rows = [], [], [], []
    reference = options["reference_condition"]
    if reference != "A0" or not 0 < options["confidence"] < 1 or options["bootstrap_replicates"] < 2:
        raise ValueError("Invalid analysis contract")
    conditions = [reference, *[name for name in config["conditions"] if name != reference]]
    inputs = []
    oof_predictions = {}
    for protocol in protocols:
        groups = splits.s1_group.to_numpy() if protocol == "S1" else splits.s2_group.to_numpy()
        unit = "numeric_signature" if protocol == "S1" else "source_address"
        interpretation = "source_group_sensitivity_random_row_split" if protocol == "S0" else "conditional_group_bootstrap_fixed_oof"
        for model, model_config in config["models"].items():
            if not model_config.get("enabled", True):
                continue
            for seed in config["seeds"]:
                predictions, scores = [], []
                for condition in conditions:
                    frame = load_cell(output, records, protocol=protocol, model=model, seed=seed,
                        condition=condition, config=config, data=data, splits=splits)
                    pred = frame.y_pred.map(mapping).to_numpy(dtype=int)
                    probabilities = validated_probabilities(frame, labels)
                    metrics, per_class, confusion = predictive_metrics(y, pred, probabilities, labels)
                    base = dict(protocol=protocol, model=model, seed=seed, condition=condition)
                    fold_scores = [record["metrics"]["f1_macro"] for record in records
                        if all(record[key] == value for key, value in base.items())]
                    pooled_rows.append({**base, **metrics, "fold_f1_mean": np.mean(fold_scores),
                        "fold_f1_sd_descriptive": np.std(fold_scores, ddof=1), "rows": len(frame)})
                    class_rows.extend({**base, **row} for row in per_class)
                    confusion_rows.extend({**base, **row} for row in confusion)
                    predictions.append(pred)
                    oof_predictions[(protocol, model, seed, condition)] = pred
                    scores.append(metrics["f1_macro"])
                result = paired_bootstrap(y, np.stack(predictions), groups, classes=len(labels),
                    replicates=options["bootstrap_replicates"], confidence=options["confidence"], seed=options["seed"])
                for index, condition in enumerate(conditions):
                    if condition == reference:
                        continue
                    low, high = result["difference_intervals"][index]
                    comparison_rows.append(dict(protocol=protocol, model=model, seed=seed, condition=condition,
                        reference=reference, f1_macro_delta=scores[index] - scores[0],
                        ci_low=low, ci_high=high, confidence=options["confidence"],
                        bootstrap_replicates=options["bootstrap_replicates"], bootstrap_seed=options["seed"],
                        groups=result["groups"], group_unit=unit, uncertainty_scope=interpretation,
                        draws_missing_any_class=result["missing_class_draws"],
                        multiplicity="unadjusted_exploratory_intervals_no_confirmatory_claim"))
    protocol_rows = []
    for target, reference_protocol in (("S1", "S0"), ("S2", "S0"), ("S2", "S1")):
        if target not in protocols or reference_protocol not in protocols:
            continue
        for model, model_config in config["models"].items():
            if not model_config.get("enabled", True):
                continue
            for seed in config["seeds"]:
                for condition in conditions:
                    pair = np.stack([oof_predictions[(reference_protocol, model, seed, condition)],
                        oof_predictions[(target, model, seed, condition)]])
                    result = paired_bootstrap(y, pair, splits.s2_group.to_numpy(), classes=len(labels),
                        replicates=options["bootstrap_replicates"], confidence=options["confidence"], seed=options["seed"])
                    low, high = result["difference_intervals"][1]
                    protocol_rows.append(dict(target_protocol=target, reference_protocol=reference_protocol,
                        model=model, seed=seed, condition=condition,
                        f1_macro_delta=macro_f1(np.bincount(y * len(labels) + pair[1],
                            minlength=len(labels) ** 2).reshape(len(labels), len(labels))) -
                            macro_f1(np.bincount(y * len(labels) + pair[0],
                                minlength=len(labels) ** 2).reshape(len(labels), len(labels))),
                        ci_low=low, ci_high=high, confidence=options["confidence"],
                        bootstrap_replicates=options["bootstrap_replicates"], bootstrap_seed=options["seed"],
                        groups=result["groups"], group_unit="source_address",
                        uncertainty_scope="source_group_sensitivity_protocol_contrast_fixed_oof",
                        draws_missing_any_class=result["missing_class_draws"],
                        interpretation="Descriptive protocol contrast; training regimes and leakage patterns differ."))
    # Write only after every requested comparison has passed completeness checks.
    report = ROOT / "reports" / config["experiment_id"]
    report.mkdir(parents=True, exist_ok=True)
    files = {}
    for name, rows in (("pooled_metrics", pooled_rows), ("class_metrics", class_rows),
        ("confusion_counts", confusion_rows), ("paired_comparisons", comparison_rows)):
        path = report / (name + ".csv")
        pd.DataFrame(rows).to_csv(path, index=False)
        files[path.name] = file_hash(path)
    confusion_frame = pd.DataFrame(confusion_rows)
    population = ["protocol", "model", "seed", "condition"]
    denominators = confusion_frame.groupby(population + ["true_class_id"])["rows"].transform("sum")
    normalized = confusion_frame.copy()
    normalized["fraction_of_true_class"] = np.divide(normalized.rows.to_numpy(dtype=float),
        denominators.to_numpy(dtype=float), out=np.zeros(len(normalized)), where=denominators.to_numpy() != 0)
    path = report / "confusion_normalized.csv"
    normalized.to_csv(path, index=False)
    files[path.name] = file_hash(path)
    if protocol_rows:
        path = report / "protocol_comparisons.csv"
        pd.DataFrame(protocol_rows).to_csv(path, index=False)
        files[path.name] = file_hash(path)
    if len(config["seeds"]) > 1:
        seed_scores = pd.DataFrame(pooled_rows).groupby(["protocol", "model", "condition"]).f1_macro.agg(
            seed_count="count", seed_mean="mean", seed_sd_descriptive="std",
            seed_min="min", seed_max="max").reset_index()
        seed_deltas = pd.DataFrame(comparison_rows).groupby(["protocol", "model", "condition"]).f1_macro_delta.agg(
            delta_seed_mean="mean", delta_seed_sd_descriptive="std",
            delta_seed_min="min", delta_seed_max="max").reset_index()
        seed_scores = seed_scores.merge(seed_deltas, how="left", on=["protocol", "model", "condition"])
        seed_scores.loc[seed_scores.condition == reference,
            ["delta_seed_mean", "delta_seed_sd_descriptive", "delta_seed_min", "delta_seed_max"]] = 0
        path = report / "seed_variation.csv"
        seed_scores.to_csv(path, index=False)
        files[path.name] = file_hash(path)
    for record in records:
        if record["protocol"] in protocols:
            inputs.append({"job_id": record["job_id"], "prediction_sha256": record["prediction_sha256"]})
    write_json(report / "analysis_manifest.json", {"experiment_id": config["experiment_id"],
        "config_sha256": manifest["config_sha256"], "dataset_sha256": manifest["dataset_sha256"],
        "split_sha256": manifest["split_sha256"], "protocols": protocols,
        "requested_protocols_complete": True, "whole_experiment_complete": manifest["complete"],
        "analysis_code_sha256": file_hash(Path(__file__)), "analysis": options,
        "prediction_inputs": inputs, "output_sha256": files,
        "limits": ["Fixed-prediction conditional intervals do not measure retraining uncertainty.",
            "Seeds are reported separately, not independent replication units.",
            "S0 source-group intervals are sensitivity analyses, not unseen-origin evaluation.",
            "Protocol contrasts resample SrcAddr as a sensitivity analysis and are not causal attribution of performance shifts.",
            "No equivalence margin, adjusted multiple testing, physical UAV or new-scenario claim."]})
    print(f"Verified analysis written to {report}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/feature_ablation_v4.json")
    parser.add_argument("--protocols", help="Comma-separated complete protocols; e.g. S2")
    args = parser.parse_args()
    analyze(args.config, protocols=None if args.protocols is None else args.protocols.split(","))


if __name__ == "__main__":
    main()
