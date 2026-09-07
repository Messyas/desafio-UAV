"""Reproducible data audit and candidate split construction for UAVIDS-2025.

The implementation follows two methodological principles:

1. Identifiers are metadata unless an operational argument supports their use.
2. Group-constrained evaluation must be defined before model selection.

These principles are motivated by the UAVIDS-2025 benchmark, the evaluation
literature listed in PLANO_CIENTIFICO_UAVIDS2025.md, and scikit-learn's
documentation on data leakage and group-aware cross-validation.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import platform
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import sklearn
from sklearn.model_selection import StratifiedGroupKFold, StratifiedKFold


RANDOM_STATE = 20260907
N_SPLITS = 5
TARGET_COLUMN = "label"
IDENTIFIER_COLUMNS = ["FlowID", "SrcAddr", "DstAddr"]
CONSTANT_CANDIDATES = ["Protocol"]
MODEL_FEATURES = [
    "FlowDuration/s",
    "SrcPort",
    "DstPort",
    "TxPackets",
    "RxPackets",
    "LostPackets",
    "TxBytes",
    "RxBytes",
    "TxPacketRate/s",
    "RxPacketRate/s",
    "TxByteRate/s",
    "RxByteRate/s",
    "MeanDelay/s",
    "MeanJitter/s",
    "Throughput/Kbps",
    "MeanPacketSize",
    "PacketDropRate",
    "AverageHopCount",
]

EXPECTED_FILE = {
    "filename": "UAVIDS-2025.csv",
    "bytes": 20_054_667,
    "rows": 122_171,
    "columns": 23,
    "md5": "ec84ed5390d5de42b07e8a011709ff82",
    "sha256": "d50d339f68be7b23f0bf089dd438b20a1835c13182d8641220538121440164d0",
    "zenodo_record": "https://zenodo.org/records/15336998",
    "zenodo_version": "v1",
    "dataset_doi": "10.5281/zenodo.15336998",
    "paper_doi": "10.1109/CNS66487.2025.11194990",
}


@dataclass(frozen=True)
class AuditPaths:
    """Paths created by the audit."""

    manifest: Path
    dictionary: Path
    summary: Path
    class_distribution: Path
    duplicates_by_class: Path
    algebraic_relations: Path
    split_candidates: Path
    fold_balance: Path
    protocol_diagnostics: Path
    fold_overlap_diagnostics: Path
    group_diagnostics: Path
    feature_ranges: Path
    class_endpoint_profile: Path
    endpoint_class_counts: Path
    report: Path


def _file_hash(path: Path, algorithm: str, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.new(algorithm)
    with path.open("rb") as stream:
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if pd.isna(value):
        return None
    return value


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(_json_ready(payload), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> np.ndarray:
    num = numerator.to_numpy(dtype=np.float64)
    den = denominator.to_numpy(dtype=np.float64)
    return np.divide(num, den, out=np.full_like(num, np.nan), where=den != 0)


def _relation_record(
    name: str,
    observed: pd.Series,
    expected: np.ndarray,
    *,
    rtol: float = 1e-5,
    atol: float = 1e-8,
) -> dict[str, Any]:
    actual = observed.to_numpy(dtype=np.float64)
    finite = np.isfinite(actual) & np.isfinite(expected)
    absolute_error = np.abs(actual[finite] - expected[finite])
    close = np.isclose(actual[finite], expected[finite], rtol=rtol, atol=atol)
    return {
        "relation": name,
        "comparable_rows": int(finite.sum()),
        "close_rows": int(close.sum()),
        "close_fraction": float(close.mean()) if close.size else np.nan,
        "mean_absolute_error": float(absolute_error.mean()) if absolute_error.size else np.nan,
        "max_absolute_error": float(absolute_error.max()) if absolute_error.size else np.nan,
        "rtol": rtol,
        "atol": atol,
    }


def _build_data_dictionary(df: pd.DataFrame) -> pd.DataFrame:
    definitions = {
        "FlowID": ("identifier", "", "Unique flow identifier; excluded from primary models"),
        "FlowDuration/s": ("numeric_feature", "s", "Total flow duration"),
        "SrcAddr": ("relational_metadata", "", "Source network address"),
        "SrcPort": ("numeric_feature", "port", "Source port"),
        "DstAddr": ("relational_metadata", "", "Destination network address"),
        "DstPort": ("numeric_feature", "port", "Destination port"),
        "Protocol": ("constant_candidate", "", "Transport/network protocol label"),
        "TxPackets": ("numeric_feature", "packets", "Transmitted packet count"),
        "RxPackets": ("numeric_feature", "packets", "Received packet count"),
        "LostPackets": ("numeric_feature", "packets", "Lost packet count"),
        "TxBytes": ("numeric_feature", "bytes", "Transmitted byte count"),
        "RxBytes": ("numeric_feature", "bytes", "Received byte count"),
        "TxPacketRate/s": ("numeric_feature", "packets/s", "Transmit packet rate"),
        "RxPacketRate/s": ("numeric_feature", "packets/s", "Receive packet rate"),
        "TxByteRate/s": ("numeric_feature", "bytes/s", "Transmit byte rate"),
        "RxByteRate/s": ("numeric_feature", "bytes/s", "Receive byte rate"),
        "MeanDelay/s": ("numeric_feature", "s", "Mean end-to-end delay"),
        "MeanJitter/s": ("numeric_feature", "s", "Mean delay variation"),
        "Throughput/Kbps": ("numeric_feature", "Kbit/s", "Effective throughput"),
        "MeanPacketSize": ("numeric_feature", "bytes", "Mean packet size"),
        "PacketDropRate": ("numeric_feature", "ratio", "Reported packet drop ratio"),
        "AverageHopCount": ("numeric_feature", "hops", "Average traversed hops"),
        "label": ("target", "class", "Traffic class"),
    }
    formulas = {
        "PacketDropRate": "reported; approximately LostPackets / TxPackets",
        "TxPacketRate/s": "reported; approximately TxPackets / FlowDuration/s",
        "RxPacketRate/s": "reported; approximately RxPackets / FlowDuration/s",
        "TxByteRate/s": "reported; approximately TxBytes / FlowDuration/s",
        "RxByteRate/s": "reported; approximately RxBytes / FlowDuration/s",
        "Throughput/Kbps": "reported; RxByteRate/s * 8 / 1000",
    }
    rows = []
    for column in df.columns:
        role, unit, definition = definitions[column]
        rows.append(
            {
                "column": column,
                "dtype": str(df[column].dtype),
                "role": role,
                "unit": unit,
                "definition": definition,
                "formula": formulas.get(column, "not confirmed"),
                "source": "UAVIDS-2025 public CSV and dataset paper",
                "unique_values": int(df[column].nunique(dropna=False)),
                "missing_values": int(df[column].isna().sum()),
                "observed_min": (
                    float(df[column].min()) if pd.api.types.is_numeric_dtype(df[column]) else ""
                ),
                "observed_max": (
                    float(df[column].max()) if pd.api.types.is_numeric_dtype(df[column]) else ""
                ),
                "domain_status": "observed_only_not_a_validated_physical_domain",
                "available_at_prediction_time": (
                    "unconfirmed" if role not in {"identifier", "target"} else "no"
                ),
                "definition_status": "provisional_from_dataset_paper",
            }
        )
    return pd.DataFrame(rows)


def _make_group_codes(frame: pd.DataFrame) -> np.ndarray:
    """Assign equal rows to one group without relying on a 64-bit hash."""

    multi_index = pd.MultiIndex.from_frame(frame, names=frame.columns.tolist())
    codes, _ = pd.factorize(multi_index, sort=False)
    return codes.astype(np.int64)


def _assign_folds(
    df: pd.DataFrame,
    signature_groups: np.ndarray,
    source_groups: np.ndarray,
) -> dict[str, np.ndarray]:
    labels = df[TARGET_COLUMN].to_numpy()
    dummy = np.zeros((len(df), 1), dtype=np.uint8)

    assignments: dict[str, np.ndarray] = {}
    splitters = {
        "s0_fold": StratifiedKFold(
            n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE
        ).split(dummy, labels),
        "s1_fold": StratifiedGroupKFold(
            n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE
        ).split(dummy, labels, groups=signature_groups),
        "s2_fold": StratifiedGroupKFold(
            n_splits=N_SPLITS, shuffle=True, random_state=RANDOM_STATE
        ).split(dummy, labels, groups=source_groups),
    }
    for protocol, folds in splitters.items():
        assignment = np.full(len(df), -1, dtype=np.int8)
        for fold_id, (_, test_indices) in enumerate(folds):
            if np.any(assignment[test_indices] != -1):
                raise AssertionError(f"Rows assigned more than once in {protocol}")
            assignment[test_indices] = fold_id
        if np.any(assignment == -1):
            raise AssertionError(f"Rows without a fold in {protocol}")
        assignments[protocol] = assignment
    return assignments


def _fold_balance(split_frame: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    protocols = ["s0_fold", "s1_fold", "s2_fold"]
    for protocol in protocols:
        for fold_id in range(N_SPLITS):
            selected = split_frame.loc[split_frame[protocol] == fold_id]
            counts = selected[TARGET_COLUMN].value_counts()
            for label, count in counts.items():
                rows.append(
                    {
                        "protocol": protocol.removesuffix("_fold").upper(),
                        "fold": fold_id,
                        "label": label,
                        "rows": int(count),
                        "fold_fraction": float(count / len(selected)),
                        "dataset_fraction": float(
                            count
                            / (split_frame[TARGET_COLUMN] == label).sum()
                        ),
                    }
                )
    return pd.DataFrame(rows)


def _protocol_diagnostics(split_frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    definitions = {
        "S0": ("s0_fold", "s1_group", "signature"),
        "S1": ("s1_fold", "s1_group", "signature"),
        "S2": ("s2_fold", "s2_group", "source"),
    }
    for name, (fold_column, group_column, group_kind) in definitions.items():
        folds_per_group = split_frame.groupby(group_column, sort=False)[
            fold_column
        ].nunique()
        rows.append(
            {
                "protocol": name,
                "group_constraint": group_kind,
                "rows": len(split_frame),
                "groups": int(split_frame[group_column].nunique()),
                "groups_crossing_folds": int((folds_per_group > 1).sum()),
                "maximum_folds_per_group": int(folds_per_group.max()),
                "minimum_fold_rows": int(
                    split_frame.groupby(fold_column, sort=False).size().min()
                ),
                "maximum_fold_rows": int(
                    split_frame.groupby(fold_column, sort=False).size().max()
                ),
            }
        )
    return pd.DataFrame(rows)


def _fold_overlap_diagnostics(
    df: pd.DataFrame, split_frame: pd.DataFrame
) -> pd.DataFrame:
    """Measure what each candidate protocol does and does not separate."""

    rows: list[dict[str, Any]] = []
    entity_columns = {
        "source_address": df["SrcAddr"].astype(str).to_numpy(),
        "destination_address": df["DstAddr"].astype(str).to_numpy(),
        "numeric_signature": split_frame["s1_group"].to_numpy(),
    }
    for protocol in ("s0", "s1", "s2"):
        folds = split_frame[f"{protocol}_fold"].to_numpy()
        for fold_id in range(N_SPLITS):
            test_mask = folds == fold_id
            train_mask = ~test_mask
            for entity, values in entity_columns.items():
                train_values = set(values[train_mask])
                test_values = set(values[test_mask])
                overlap = train_values.intersection(test_values)
                rows.append(
                    {
                        "protocol": protocol.upper(),
                        "fold": fold_id,
                        "entity": entity,
                        "train_unique": len(train_values),
                        "test_unique": len(test_values),
                        "overlap_unique": len(overlap),
                        "test_overlap_fraction": (
                            len(overlap) / len(test_values) if test_values else np.nan
                        ),
                    }
                )
    return pd.DataFrame(rows)


def _group_diagnostics(
    df: pd.DataFrame, signature_groups: np.ndarray, source_groups: np.ndarray
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for name, groups in (
        ("numeric_signature", signature_groups),
        ("source_address", source_groups),
    ):
        grouped = pd.DataFrame({"group": groups, "label": df[TARGET_COLUMN]}).groupby(
            "group", sort=False
        )
        sizes = grouped.size()
        class_counts = grouped["label"].nunique()
        rows.append(
            {
                "group_type": name,
                "groups": int(len(sizes)),
                "minimum_rows": int(sizes.min()),
                "median_rows": float(sizes.median()),
                "mean_rows": float(sizes.mean()),
                "maximum_rows": int(sizes.max()),
                "groups_with_multiple_labels": int((class_counts > 1).sum()),
            }
        )
    return pd.DataFrame(rows)


def _feature_ranges(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for column in df.select_dtypes(include=[np.number]).columns:
        values = df[column]
        rows.append(
            {
                "column": column,
                "minimum": float(values.min()),
                "median": float(values.median()),
                "maximum": float(values.max()),
                "zero_rows": int((values == 0).sum()),
                "negative_rows": int((values < 0).sum()),
            }
        )
    return pd.DataFrame(rows)


def _class_endpoint_profile(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(TARGET_COLUMN, dropna=False)
        .agg(
            rows=("FlowID", "size"),
            source_addresses=("SrcAddr", "nunique"),
            destination_addresses=("DstAddr", "nunique"),
            source_ports=("SrcPort", "nunique"),
            destination_ports=("DstPort", "nunique"),
            minimum_flow_id=("FlowID", "min"),
            maximum_flow_id=("FlowID", "max"),
        )
        .reset_index()
    )


def _endpoint_class_counts(df: pd.DataFrame) -> pd.DataFrame:
    frames = []
    for endpoint_type, column in (
        ("source", "SrcAddr"),
        ("destination", "DstAddr"),
    ):
        counts = (
            df.groupby([column, TARGET_COLUMN], dropna=False)
            .size()
            .reset_index(name="rows")
            .rename(columns={column: "address"})
        )
        counts.insert(0, "endpoint_type", endpoint_type)
        frames.append(counts)
    return pd.concat(frames, ignore_index=True)


def _write_split_candidates(path: Path, split_frame: pd.DataFrame) -> None:
    # Fixing gzip's timestamp makes the compressed artifact reproducible.
    with path.open("wb") as raw_stream:
        with gzip.GzipFile(
            filename="split_candidates.csv", mode="wb", fileobj=raw_stream, mtime=0
        ) as gzip_stream:
            split_frame.to_csv(gzip_stream, index=False, lineterminator="\n")


def run_data_audit(dataset_path: Path, output_dir: Path) -> tuple[AuditPaths, dict[str, Any]]:
    """Audit the dataset and build candidate S0/S1/S2 fold manifests."""

    dataset_path = dataset_path.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    file_size = dataset_path.stat().st_size
    md5 = _file_hash(dataset_path, "md5")
    sha256 = _file_hash(dataset_path, "sha256")
    df = pd.read_csv(dataset_path)

    observed_columns = df.columns.tolist()
    missing_expected_columns = sorted(
        set(MODEL_FEATURES + IDENTIFIER_COLUMNS + CONSTANT_CANDIDATES + [TARGET_COLUMN])
        - set(observed_columns)
    )
    if missing_expected_columns:
        raise ValueError(f"Missing expected columns: {missing_expected_columns}")

    exact_zenodo_match = (
        file_size == EXPECTED_FILE["bytes"]
        and len(df) == EXPECTED_FILE["rows"]
        and len(df.columns) == EXPECTED_FILE["columns"]
        and md5 == EXPECTED_FILE["md5"]
        and sha256 == EXPECTED_FILE["sha256"]
    )
    if not exact_zenodo_match:
        raise ValueError("Local dataset does not match the registered Zenodo v1 artifact")

    dictionary = _build_data_dictionary(df)
    class_distribution = (
        df[TARGET_COLUMN]
        .value_counts(dropna=False)
        .rename_axis(TARGET_COLUMN)
        .reset_index(name="rows")
    )
    class_distribution["fraction"] = class_distribution["rows"] / len(df)

    full_duplicates = df.duplicated(keep=False)
    model_duplicates = df.duplicated(subset=MODEL_FEATURES, keep=False)
    model_signature_unique_duplicates = df.duplicated(
        subset=MODEL_FEATURES, keep="first"
    )
    signature_label_unique_duplicates = df.duplicated(
        subset=MODEL_FEATURES + [TARGET_COLUMN], keep="first"
    )
    label_counts_per_signature = df.groupby(MODEL_FEATURES, dropna=False)[
        TARGET_COLUMN
    ].nunique()
    conflicting_signatures = int((label_counts_per_signature > 1).sum())

    duplicates_by_class = (
        df.assign(_is_repeated_signature=model_duplicates)
        .groupby(TARGET_COLUMN, dropna=False)["_is_repeated_signature"]
        .agg(rows="size", rows_in_repeated_signature="sum", fraction="mean")
        .reset_index()
    )

    algebraic_relations = pd.DataFrame(
        [
            _relation_record(
                "PacketDropRate ~= LostPackets / TxPackets",
                df["PacketDropRate"],
                _safe_divide(df["LostPackets"], df["TxPackets"]),
            ),
            _relation_record(
                "TxPacketRate/s ~= TxPackets / FlowDuration/s",
                df["TxPacketRate/s"],
                _safe_divide(df["TxPackets"], df["FlowDuration/s"]),
            ),
            _relation_record(
                "RxPacketRate/s ~= RxPackets / FlowDuration/s",
                df["RxPacketRate/s"],
                _safe_divide(df["RxPackets"], df["FlowDuration/s"]),
            ),
            _relation_record(
                "TxByteRate/s ~= TxBytes / FlowDuration/s",
                df["TxByteRate/s"],
                _safe_divide(df["TxBytes"], df["FlowDuration/s"]),
            ),
            _relation_record(
                "RxByteRate/s ~= RxBytes / FlowDuration/s",
                df["RxByteRate/s"],
                _safe_divide(df["RxBytes"], df["FlowDuration/s"]),
            ),
            _relation_record(
                "Throughput/Kbps ~= RxByteRate/s * 8 / 1000",
                df["Throughput/Kbps"],
                df["RxByteRate/s"].to_numpy(dtype=np.float64) * 8 / 1000,
            ),
        ]
    )

    signature_groups = _make_group_codes(df[MODEL_FEATURES])
    source_groups, source_values = pd.factorize(df["SrcAddr"], sort=True)
    assignments = _assign_folds(df, signature_groups, source_groups)
    split_frame = pd.DataFrame(
        {
            "row_id": np.arange(len(df), dtype=np.int64),
            "flow_id": df["FlowID"].to_numpy(),
            TARGET_COLUMN: df[TARGET_COLUMN].to_numpy(),
            "s1_group": signature_groups,
            "s2_group": source_groups.astype(np.int64),
            **assignments,
        }
    )
    fold_balance = _fold_balance(split_frame)
    protocol_diagnostics = _protocol_diagnostics(split_frame)
    fold_overlap_diagnostics = _fold_overlap_diagnostics(df, split_frame)
    group_diagnostics = _group_diagnostics(df, signature_groups, source_groups)
    feature_ranges = _feature_ranges(df)
    class_endpoint_profile = _class_endpoint_profile(df)
    endpoint_class_counts = _endpoint_class_counts(df)

    expected_labels = set(df[TARGET_COLUMN].unique())
    observed_fold_labels = (
        fold_balance.groupby(["protocol", "fold"])[TARGET_COLUMN].agg(set)
    )
    if not observed_fold_labels.map(lambda labels: labels == expected_labels).all():
        raise AssertionError("At least one candidate fold is missing a class")
    constrained = protocol_diagnostics["protocol"].isin(["S1", "S2"])
    if (protocol_diagnostics.loc[constrained, "groups_crossing_folds"] != 0).any():
        raise AssertionError("A constrained group crosses candidate folds")

    pdr_above_one = int((df["PacketDropRate"] > 1).sum())
    pdr_below_zero = int((df["PacketDropRate"] < 0).sum())
    constant_columns = [column for column in df.columns if df[column].nunique() <= 1]
    flow_id_sequential = bool(
        np.array_equal(df["FlowID"].to_numpy(), np.arange(1, len(df) + 1))
    )
    adjacent_same_label_fraction = float(
        (df[TARGET_COLUMN].to_numpy()[1:] == df[TARGET_COLUMN].to_numpy()[:-1]).mean()
    )

    manifest = {
        "dataset": {
            "path_recorded_as": dataset_path.name,
            "bytes": file_size,
            "rows": len(df),
            "columns": len(df.columns),
            "column_names": observed_columns,
            "md5": md5,
            "sha256": sha256,
            "exact_match_to_registered_zenodo_v1": exact_zenodo_match,
        },
        "registered_source": EXPECTED_FILE,
        "environment": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
        "audit_configuration": {
            "random_state": RANDOM_STATE,
            "candidate_outer_folds": N_SPLITS,
            "target": TARGET_COLUMN,
            "identifier_columns": IDENTIFIER_COLUMNS,
            "model_features_for_signature": MODEL_FEATURES,
            "status": "candidate_splits_not_frozen_for_final_experiments",
        },
    }

    summary = {
        "rows": len(df),
        "columns": len(df.columns),
        "classes": int(df[TARGET_COLUMN].nunique()),
        "missing_cells": int(df.isna().sum().sum()),
        "infinite_numeric_cells": int(
            np.isinf(df.select_dtypes(include=[np.number]).to_numpy()).sum()
        ),
        "constant_columns": constant_columns,
        "full_duplicate_rows_after_first": int(df.duplicated().sum()),
        "unique_model_signatures": int(len(df) - model_signature_unique_duplicates.sum()),
        "duplicate_model_signature_rows_after_first": int(
            model_signature_unique_duplicates.sum()
        ),
        "duplicate_signature_and_label_rows_after_first": int(
            signature_label_unique_duplicates.sum()
        ),
        "rows_belonging_to_repeated_model_signatures": int(model_duplicates.sum()),
        "conflicting_model_signatures": conflicting_signatures,
        "packet_drop_rate_above_one": pdr_above_one,
        "packet_drop_rate_below_zero": pdr_below_zero,
        "flow_id_unique": bool(df["FlowID"].is_unique),
        "flow_id_sequential_in_file_order": flow_id_sequential,
        "adjacent_same_label_fraction": adjacent_same_label_fraction,
        "source_addresses": int(len(source_values)),
        "destination_addresses": int(df["DstAddr"].nunique()),
        "protocol_values": sorted(df["Protocol"].dropna().astype(str).unique().tolist()),
        "interpretation_limits": [
            "The public CSV has no explicit timestamp, session_id, simulation_id, or scenario_id.",
            "FlowID sequence is not treated as validated chronology.",
            "S1 evaluates unseen exact numeric signatures; it does not reconstruct sessions.",
            "S2 evaluates unseen source addresses; it does not prove unseen physical UAVs.",
            "Feature availability at an onboard detector remains unconfirmed.",
        ],
    }

    paths = AuditPaths(
        manifest=output_dir / "data_manifest.json",
        dictionary=output_dir / "data_dictionary.csv",
        summary=output_dir / "data_audit_summary.json",
        class_distribution=output_dir / "class_distribution.csv",
        duplicates_by_class=output_dir / "duplicates_by_class.csv",
        algebraic_relations=output_dir / "algebraic_relations.csv",
        split_candidates=output_dir / "split_candidates.csv.gz",
        fold_balance=output_dir / "fold_balance.csv",
        protocol_diagnostics=output_dir / "protocol_diagnostics.csv",
        fold_overlap_diagnostics=output_dir / "fold_overlap_diagnostics.csv",
        group_diagnostics=output_dir / "group_diagnostics.csv",
        feature_ranges=output_dir / "feature_ranges.csv",
        class_endpoint_profile=output_dir / "class_endpoint_profile.csv",
        endpoint_class_counts=output_dir / "endpoint_class_counts.csv",
        report=output_dir / "README.md",
    )
    dictionary.to_csv(paths.dictionary, index=False, lineterminator="\n")
    _write_json(paths.summary, summary)
    class_distribution.to_csv(paths.class_distribution, index=False, lineterminator="\n")
    duplicates_by_class.to_csv(paths.duplicates_by_class, index=False, lineterminator="\n")
    algebraic_relations.to_csv(paths.algebraic_relations, index=False, lineterminator="\n")
    _write_split_candidates(paths.split_candidates, split_frame)
    manifest["candidate_split_artifact"] = {
        "path_recorded_as": paths.split_candidates.name,
        "sha256": _file_hash(paths.split_candidates, "sha256"),
        "status": "candidate_not_final",
    }
    _write_json(paths.manifest, manifest)
    fold_balance.to_csv(paths.fold_balance, index=False, lineterminator="\n")
    protocol_diagnostics.to_csv(paths.protocol_diagnostics, index=False, lineterminator="\n")
    fold_overlap_diagnostics.to_csv(
        paths.fold_overlap_diagnostics, index=False, lineterminator="\n"
    )
    group_diagnostics.to_csv(paths.group_diagnostics, index=False, lineterminator="\n")
    feature_ranges.to_csv(paths.feature_ranges, index=False, lineterminator="\n")
    class_endpoint_profile.to_csv(
        paths.class_endpoint_profile, index=False, lineterminator="\n"
    )
    endpoint_class_counts.to_csv(
        paths.endpoint_class_counts, index=False, lineterminator="\n"
    )

    report = f"""# Auditoria reproduzível do UAVIDS-2025

Esta pasta foi gerada por `src/uavids_study/data_audit.py`. Os resultados descrevem o arquivo público, não o desempenho de classificadores.

## Identidade do artefato

- Registros: {summary['rows']:,}
- Colunas: {summary['columns']}
- MD5: `{md5}`
- SHA-256: `{sha256}`
- Correspondência exata com Zenodo v1: `{exact_zenodo_match}`

## Achados estruturais

- Células ausentes: {summary['missing_cells']}
- Colunas constantes: {', '.join(constant_columns)}
- Assinaturas numéricas únicas: {summary['unique_model_signatures']:,}
- Linhas repetidas além da primeira por assinatura: {summary['duplicate_model_signature_rows_after_first']:,}
- Linhas pertencentes a assinaturas repetidas: {summary['rows_belonging_to_repeated_model_signatures']:,}
- Assinaturas associadas a mais de um rótulo: {conflicting_signatures:,}
- `PacketDropRate > 1`: {pdr_above_one:,}
- `FlowID` único e sequencial na ordem do arquivo: `{summary['flow_id_unique']}` / `{flow_id_sequential}`
- A ordem do arquivo mantém o mesmo rótulo entre linhas adjacentes em {summary['adjacent_same_label_fraction']:.2%} dos pares.

## Protocolos candidatos

- S0: folds estratificados aleatórios; referência, sem restrição de grupos.
- S1: folds estratificados por grupos de assinaturas numéricas exatas.
- S2: folds estratificados por endereço de origem.

Esses folds são **candidatos**. A composição deve ser revisada antes de congelar o protocolo final. S1 não equivale a sessão e S2 não equivale necessariamente a UAV físico.

Os arquivos `fold_overlap_diagnostics.csv` e `group_diagnostics.csv` explicitam as sobreposições residuais e o desequilíbrio dos grupos. Eles devem acompanhar qualquer resultado produzido com S0/S1/S2.

## Limites atuais

O CSV não contém timestamp, sessão, execução ou cenário explícitos. Assim, esta etapa não autoriza sequência temporal, divisão por execução ou cálculo do tempo desde o início de um ataque. A disponibilidade causal/local dos atributos também permanece pendente de confirmação dos autores.
"""
    paths.report.write_text(report, encoding="utf-8")
    return paths, summary


if __name__ == "__main__":
    project_root = Path(__file__).resolve().parents[2]
    dataset = project_root / "notebooks" / "data" / "raw" / "UAVIDS-2025.csv"
    output = project_root / "research_artifacts" / "data_audit"
    created_paths, audit_summary = run_data_audit(dataset, output)
    print(json.dumps(_json_ready(audit_summary), ensure_ascii=False, indent=2))
    print(f"Artifacts: {created_paths.report.parent}")
