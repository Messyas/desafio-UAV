"""Descriptive diagnostics only: never provide corpus-wide imputation statistics."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.uavids_study.features import DerivedFeatures, RATIOS
from src.uavids_study.predictive_experiment import file_hash, write_json


def main():
    config = json.loads((ROOT / "configs/feature_ablation_v4.json").read_text("utf-8"))
    path = ROOT / "notebooks/data/raw/UAVIDS-2025.csv"
    data = pd.read_csv(path)
    names = list(RATIOS)
    values = DerivedFeatures(config["primary_features"], names).fit_transform(data[config["primary_features"]])[:, -3:]
    rows = []
    for index, name in enumerate(names):
        num, den = RATIOS[name]
        finite = values[:, index][np.isfinite(values[:, index])]
        rows.append(dict(feature=name, numerator=num, denominator=den,
            invalid_denominator_rows=int((data[den] <= 0).sum()), missing_derived_rows=int(np.isnan(values[:, index]).sum()),
            finite_rows=len(finite), minimum=float(finite.min()) if len(finite) else None,
            median=float(np.median(finite)) if len(finite) else None,
            maximum=float(finite.max()) if len(finite) else None,
            unit="dimensionless" if name != "throughput_per_hop" else "Kbps/hop"))
    loss = pd.Series(values[:, 0])
    pdr = data.PacketDropRate
    valid = loss.notna()
    pearson, spearman = loss.corr(pdr), loss.corr(pdr, method="spearman")
    report = ROOT / "research_artifacts/derived_features"
    report.mkdir(parents=True, exist_ok=True)
    table = report / "feature_diagnostics.csv"
    pd.DataFrame(rows).to_csv(table, index=False)
    by_class = []
    for label in config["class_order"]:
        selected = data.label == label
        for index, name in enumerate(names):
            by_class.append({"class_name": label, "feature": name, "rows": int(selected.sum()),
                "missing_derived_rows": int(np.isnan(values[selected, index]).sum()),
                "missing_fraction": float(np.isnan(values[selected, index]).mean())})
    class_table = report / "missing_by_class.csv"
    pd.DataFrame(by_class).to_csv(class_table, index=False)
    write_json(report / "audit_manifest.json", {"dataset_sha256": file_hash(path), "rows": len(data),
        "table_sha256": file_hash(table), "missing_by_class_sha256": file_hash(class_table),
        "packet_drop_rate_above_one_rows": int((pdr > 1).sum()),
        "loss_ratio_vs_packet_drop_rate": {"comparable_rows": int(valid.sum()),
            "pearson": float(pearson) if np.isfinite(pearson) else None,
            "spearman": float(spearman) if np.isfinite(spearman) else None,
            "close_rows_atol_1e_8_rtol_1e_5": int(np.isclose(loss[valid], pdr[valid], atol=1e-8, rtol=1e-5).sum())},
        "interpretation": "Corpus-wide descriptive audit, not training preprocessing or proof of feature novelty.",
        "invalid_ratio_policy": "denominator <= 0 or overflow -> NaN; train-fold median; all-missing train column -> 0"})
    print(table)


if __name__ == "__main__":
    main()
