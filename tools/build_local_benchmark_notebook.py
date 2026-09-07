"""Build the report and notebook for local inference benchmark v1."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = ROOT / "benchmarks" / "local_inference_v1"
REPORT_DIR = ROOT / "reports" / "local_inference_v1"
NOTEBOOK_PATH = ROOT / "notebooks" / "research" / "04_benchmark_local.ipynb"


def markdown(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(True)}


def code(source: str, output: str, count: int) -> dict:
    return {
        "cell_type": "code",
        "execution_count": count,
        "metadata": {},
        "outputs": [{"name": "stdout", "output_type": "stream", "text": (output.rstrip() + "\n").splitlines(True)}],
        "source": source.splitlines(True),
    }


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((BENCHMARK_DIR / "manifest.json").read_text("utf-8"))
    summaries = [
        json.loads((BENCHMARK_DIR / name).read_text("utf-8"))
        for name in manifest["model_summaries"]
    ]
    individual = pd.DataFrame(
        [
            {
                "model": item["model"],
                "model_mib": item["model_bytes"] / (1024**2),
                "load_ms": item["load_seconds"] * 1000,
                "rss_load_delta_mib": item["rss_load_delta_bytes"] / (1024**2),
                **item["individual"],
            }
            for item in summaries
        ]
    )
    batch_rows = []
    for item in summaries:
        batch_rows.extend({"model": item["model"], **row} for row in item["batches"])
    batches = pd.DataFrame(batch_rows)
    individual.to_csv(REPORT_DIR / "individual_latency.csv", index=False, lineterminator="\n")
    batches.to_csv(REPORT_DIR / "batch_latency.csv", index=False, lineterminator="\n")

    fig, axis = plt.subplots(figsize=(8.5, 5.2))
    for model, selected in batches.groupby("model"):
        axis.plot(
            selected["batch_size"],
            selected["amortized_p50_us_per_row"],
            marker="o",
            linewidth=2,
            label="XGBoost" if model == "xgboost" else "Random Forest",
        )
    axis.set_xscale("log", base=2)
    axis.set_yscale("log")
    axis.set_xlabel("Tamanho do lote")
    axis.set_ylabel("P50 amortizado por linha (µs, escala log)")
    axis.set_title("Inferência local: efeito do lote")
    axis.grid(alpha=0.25, which="both")
    axis.legend()
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "batch_amortization.png", dpi=180)
    plt.close(fig)

    xgb = individual.query("model == 'xgboost'").iloc[0]
    rf = individual.query("model == 'random_forest'").iloc[0]
    latency_ratio = rf.p50_us / xgb.p50_us
    size_ratio = rf.model_mib / xgb.model_mib
    report = f"""# Benchmark local em processo — piloto v1

- XGBoost: P50 {xgb.p50_us:.2f} µs, P95 {xgb.p95_us:.2f} µs, P99 {xgb.p99_us:.2f} µs em 5.000 chamadas individuais.
- Random Forest: P50 {rf.p50_us:.2f} µs, P95 {rf.p95_us:.2f} µs, P99 {rf.p99_us:.2f} µs em 5.000 chamadas individuais.
- Neste host, RF teve P50 {latency_ratio:.1f} vezes maior e artefato {size_ratio:.1f} vezes maior.
- Em lote 1.024, o P50 amortizado foi {batches.query("model == 'xgboost' and batch_size == 1024").amortized_p50_us_per_row.iloc[0]:.2f} µs/linha para XGBoost e {batches.query("model == 'random_forest' and batch_size == 1024").amortized_p50_us_per_row.iloc[0]:.2f} µs/linha para RF.

Esses valores medem `predict_proba` com entrada NumPy pronta em Windows. Não incluem rede, serialização, extração de fluxo ou fila. O host não foi dedicado e os modelos foram medidos em processos separados. O resultado apoia XGBoost como candidato para o benchmark em container, mas não equivale a latência embarcada nem a P99 de requisição.
"""
    (REPORT_DIR / "README.md").write_text(report, encoding="utf-8")

    individual_view = individual.round(3)
    batch_view = batches.round(3)
    cells = [
        markdown("""# UAVIDS-2025 — benchmark local de inferência

Este notebook apresenta a primeira medição de sistemas dos artefatos congelados. A fronteira começa imediatamente antes de `predict_proba` e termina no retorno das probabilidades. A leitura do CSV, a rede e a serialização não participam do tempo."""),
        markdown("""## Protocolo e cautela

O procedimento está em [`local_benchmark_v1.md`](../../protocol/local_benchmark_v1.md). Foram feitas 200 chamadas de aquecimento e cinco repetições, totalizando 5.000 chamadas individuais por modelo. Os dados de duração brutos foram preservados. Este é um piloto em Windows compartilhado, sem restrição de CPU/RAM."""),
        code("""from pathlib import Path
import json
import pandas as pd

project_root = Path.cwd().resolve()
if project_root.name == "research":
    project_root = project_root.parents[1]
elif project_root.name == "notebooks":
    project_root = project_root.parent
benchmark_dir = project_root / "benchmarks" / "local_inference_v1"
report_dir = project_root / "reports" / "local_inference_v1"
manifest = json.loads((benchmark_dir / "manifest.json").read_text("utf-8"))
print(json.dumps(manifest, indent=2, ensure_ascii=False))""", json.dumps(manifest, indent=2, ensure_ascii=False), 1),
        markdown("## Latência individual, carregamento e memória residente"),
        code("""individual = pd.read_csv(report_dir / "individual_latency.csv")
print(individual.round(3).to_string(index=False))""", individual_view.to_string(index=False), 2),
        markdown(f"""XGBoost apresentou P50 **{xgb.p50_us:.2f} µs** e P99 **{xgb.p99_us:.2f} µs**. RF apresentou P50 **{rf.p50_us:.2f} µs** e P99 **{rf.p99_us:.2f} µs**. A diferença de P50 foi de {latency_ratio:.1f} vezes neste host."""),
        markdown("## Lotes e custo amortizado"),
        code("""batches = pd.read_csv(report_dir / "batch_latency.csv")
print(batches.round(3).to_string(index=False))""", batch_view.to_string(index=False), 3),
        markdown("![Amortização por lote](../../reports/local_inference_v1/batch_amortization.png)"),
        markdown("""## Conclusão operacional limitada

XGBoost é o candidato preferencial para medir requisição em container porque manteve a melhor qualidade média, usa artefato muito menor e foi substancialmente mais rápido neste piloto. RF permanece como comparador. A próxima bancada deve usar exatamente os hashes congelados, medir cliente–servidor e registrar recursos/limites efetivamente aplicados. Não se infere desempenho em drone a partir deste host."""),
    ]
    notebook = {
        "cells": cells,
        "metadata": {"kernelspec": {"display_name": "Python 3 (.venv)", "language": "python", "name": "python3"}, "language_info": {"name": "python", "version": "3.12.10"}},
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    NOTEBOOK_PATH.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(NOTEBOOK_PATH)


if __name__ == "__main__":
    main()
