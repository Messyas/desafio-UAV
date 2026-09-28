"""Join verified S2 OOF quality to resource-limited systems cost, or mark pending."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from uavids_study.predictive_experiment import file_hash, json_hash, write_json


def build(project_root: Path, config_path: Path | None = None) -> pd.DataFrame:
    config_path = config_path or project_root / "configs/docker_latency_v4.json"
    config = json.loads(config_path.read_text("utf-8"))
    deployment = json.loads((project_root / "configs/deployment_latency_v2.json").read_text("utf-8"))
    baseline = json.loads((project_root / deployment["predictive_reference"]).read_text("utf-8"))
    for key, other in (("features", "primary_features"), ("class_order", "class_order"),
                       ("random_seed", "random_seed"), ("threads", "threads")):
        if deployment[key] != baseline[other]:
            raise ValueError(f"Predictive/deployment mismatch: {key}")
    for name in config["models"]:
        if deployment["models"][name] != baseline["models"][name]:
            raise ValueError(f"Predictive/deployment model mismatch: {name}")
    quality_dir = project_root / "results" / baseline["experiment_id"]
    quality_manifest = json.loads((quality_dir / "experiment_manifest.json").read_text("utf-8"))
    if not quality_manifest["complete"] or quality_manifest["config_sha256"] != json_hash(baseline):
        raise ValueError("Predictive reference is incomplete or has changed")
    quality_path = quality_dir / "metrics_pooled_oof.csv"
    quality = pd.read_csv(quality_path)
    artifact_dir = project_root / "artifacts/models" / config["artifact_set_id"]
    manifest = json.loads((artifact_dir / "manifest.json").read_text("utf-8"))
    if manifest["config_sha256"] != json_hash(deployment):
        raise ValueError("Frozen deployment configuration mismatch")
    if manifest["dataset_sha256"] != quality_manifest["dataset_sha256"]:
        raise ValueError("Predictive/deployment dataset mismatch")
    frozen = {item["model"]: item for item in manifest["models"]}
    benchmark_dir = project_root / "benchmarks" / config["benchmark_id"]
    rows = []
    for name in config["models"]:
        selected = quality.loc[(quality.protocol == "S2") & (quality.model == name)
                               & (quality.seed == config["random_seed"])]
        if len(selected) != 1 or int(selected.iloc[0].folds_combined) != 5:
            raise ValueError(f"Missing complete S2 OOF quality: {name}")
        record = frozen[name]
        if file_hash(artifact_dir / record["file"]) != record["sha256"]:
            raise ValueError(f"Frozen artifact changed: {name}")
        row = {"model": name, "s2_oof_f1_macro": float(selected.iloc[0].f1_macro),
               "model_mib": record["bytes"] / 1024**2, "latency_status": "pending",
               "http_p50_ms": None, "http_p95_ms": None, "http_p99_ms": None,
               "predict_p50_ms": None, "memory_peak_mib": None, "failure": ""}
        summary_path = benchmark_dir / f"{name}__summary.json"
        failure_path = benchmark_dir / f"{name}__failure.json"
        if failure_path.exists():
            failure = json.loads(failure_path.read_text("utf-8"))
            if failure["config_sha256"] != json_hash(config):
                raise ValueError(f"Stale failure record: {name}")
            row.update(latency_status="failed", failure=failure["message"])
            diagnostics_path = benchmark_dir / f"{name}__container_failure.json"
            if diagnostics_path.exists():
                diagnostics = json.loads(diagnostics_path.read_text("utf-8"))
                state = diagnostics.get("container_inspect", {})
                if isinstance(state, dict) and state.get("State", {}).get("OOMKilled"):
                    row["failure"] = "OOMKilled during startup under the memory limit"
        elif summary_path.exists():
            summary = json.loads(summary_path.read_text("utf-8"))
            if (summary["model_sha256"] != record["sha256"]
                    or summary["config_sha256"] != json_hash(config)):
                raise ValueError(f"Stale systems result: {name}")
            for filename, checksum in summary["files"].items():
                if file_hash(benchmark_dir / filename) != checksum:
                    raise ValueError(f"Systems raw record changed: {filename}")
            row.update(latency_status="complete",
                       predict_p50_ms=summary["individual_server_predict"]["p50_us"] / 1000,
                       memory_peak_mib=summary["resources"]["memory_mib_max"])
            for q in (50, 95, 99):
                row[f"http_p{q}_ms"] = summary["individual_client"][f"p{q}_us"] / 1000
        rows.append(row)
    result = pd.DataFrame(rows)
    report_dir = project_root / "reports" / config["benchmark_id"]
    report_dir.mkdir(parents=True, exist_ok=True)
    result.to_csv(report_dir / "quality_latency_comparison.csv", index=False)
    lines = [f"# Comparação de qualidade e latência — {config['benchmark_id']}", "",
             f"Limites: {config['cpu_limit']} CPU, {config['memory_limit']}; "
             f"{config['model_threads']} thread(s) de inferência. Mesmas entradas por modelo.", "",
             "| Modelo | F1-macro OOF S2 | HTTP P50 (ms) | HTTP P95 (ms) | Situação |",
             "|---|---:|---:|---:|---|"]
    for row in rows:
        p50 = "—" if row["http_p50_ms"] is None else f"{row['http_p50_ms']:.3f}"
        p95 = "—" if row["http_p95_ms"] is None else f"{row['http_p95_ms']:.3f}"
        status = row["failure"] or row["latency_status"]
        lines.append(f"| {row['model']} | {row['s2_oof_f1_macro']:.6f} | {p50} | {p95} | {status} |")
    lines.extend(["", "Qualidade: procedimento da baseline v1 em S2; custo: artefatos "
                  "reajustados em todos os dados. Não são métricas de treinamento desses artefatos.",
                  "A latência HTTP exclui coleta de fluxos e cálculo dos atributos. Quantis "
                  "de uma sessão são descritivos; ordem fixa e carga do host limitam o ranking.",
                  "Falhas de memória não recebem latência numérica; latências pendentes não são estimadas."])
    (report_dir / "COMPARISON.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    write_json(report_dir / "comparison_manifest.json", {
        "config_sha256": json_hash(config), "quality_table_sha256": file_hash(quality_path),
        "quality_manifest_sha256": file_hash(quality_dir / "experiment_manifest.json"),
        "artifact_manifest_sha256": file_hash(artifact_dir / "manifest.json"),
        "quality_scope": "historical S2 OOF procedure; not quality of full-data frozen artifact",
        "complete": bool((result.latency_status == "complete").all()),
    })
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()
    print(build(Path(__file__).resolve().parents[1], args.config).to_string(index=False))
