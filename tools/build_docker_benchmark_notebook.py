"""Build the analysis notebook for the final local Docker benchmark."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DIR = ROOT / "benchmarks" / "docker_local_v2"
REPORT_DIR = ROOT / "reports" / "docker_local_v2"
NOTEBOOK_PATH = ROOT / "notebooks" / "research" / "05_benchmark_docker_local.ipynb"


def markdown(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(True)}


def code(source: str, output: str, count: int) -> dict:
    return {
        "cell_type": "code",
        "execution_count": count,
        "metadata": {},
        "outputs": [
            {
                "name": "stdout",
                "output_type": "stream",
                "text": (output.rstrip() + "\n").splitlines(True),
            }
        ],
        "source": source.splitlines(True),
    }


def main() -> None:
    manifest = json.loads((BENCHMARK_DIR / "manifest.json").read_text("utf-8"))
    latency = pd.read_csv(REPORT_DIR / "individual_http_latency.csv")
    batches = pd.read_csv(REPORT_DIR / "batch_http_latency.csv")
    throughput = pd.read_csv(REPORT_DIR / "throughput.csv")
    resources = pd.read_csv(REPORT_DIR / "resource_usage.csv")
    tradeoff = pd.read_csv(REPORT_DIR / "quality_cost_tradeoff.csv")

    xgb = tradeoff.query("model == 'xgboost'").iloc[0]
    rf = tradeoff.query("model == 'random_forest'").iloc[0]
    latency_ratio = rf.docker_http_p50_ms / xgb.docker_http_p50_ms
    memory_ratio = rf.memory_mib_max / xgb.memory_mib_max
    size_ratio = rf.model_mib / xgb.model_mib
    f1_difference = xgb.s2_f1_macro_mean - rf.s2_f1_macro_mean

    cells = [
        markdown(
            """# UAVIDS-2025 — benchmark Docker local

Este notebook analisa a rodada final `docker_local_v2`. A pergunta é restrita: qual é o custo de servir os artefatos congelados de XGBoost e Random Forest por HTTP local, em containers separados com 0,5 CPU e 512 MiB?

CNN, GNN, stacking, Kubernetes, energia e rede entre máquinas estão fora do escopo. O protocolo foi congelado antes da v2 em [`docker_local_v2.md`](../../protocol/docker_local_v2.md)."""
        ),
        markdown(
            """## Por que existe uma versão 2?

O piloto v1 apresentou cerca de 45 ms constantes fora de `predict_proba`, compatíveis com Nagle/delayed ACK em mensagens pequenas. A v1 foi descartada, `TCP_NODELAY` foi registrado como correção e os dois modelos foram repetidos integralmente. Esta decisão está em [`deviations.md`](../../protocol/deviations.md); nenhum número da v1 deve entrar no artigo."""
        ),
        code(
            """from pathlib import Path
import json
import pandas as pd

project_root = Path.cwd().resolve()
if project_root.name == "research":
    project_root = project_root.parents[1]
elif project_root.name == "notebooks":
    project_root = project_root.parent
benchmark_dir = project_root / "benchmarks" / "docker_local_v2"
report_dir = project_root / "reports" / "docker_local_v2"
manifest = json.loads((benchmark_dir / "manifest.json").read_text("utf-8"))
print({
    "status": manifest["status"],
    "image_id": manifest["image_id"],
    "docker": manifest["docker_version"]["Server"]["Platform"]["Name"],
    "kernel": manifest["docker_version"]["Server"]["KernelVersion"],
    "models": manifest["models"],
})""",
            str(
                {
                    "status": manifest["status"],
                    "image_id": manifest["image_id"],
                    "docker": manifest["docker_version"]["Server"]["Platform"]["Name"],
                    "kernel": manifest["docker_version"]["Server"]["KernelVersion"],
                    "models": manifest["models"],
                }
            ),
            1,
        ),
        markdown(
            """## Latência HTTP individual

O cronômetro do cliente começa com o corpo JSON já serializado e termina após a leitura integral da resposta. Portanto, inclui transporte local, parsing no servidor, fila, inferência e serialização da resposta. O tempo interno de `predict_proba` também foi registrado separadamente."""
        ),
        code(
            """latency = pd.read_csv(report_dir / "individual_http_latency.csv")
print(latency.round(3).to_string(index=False))""",
            latency.round(3).to_string(index=False),
            2,
        ),
        markdown(
            f"""XGBoost apresentou P50 HTTP de **{xgb.docker_http_p50_ms:.3f} ms**; Random Forest, **{rf.docker_http_p50_ms:.3f} ms**. Nesta bancada, a mediana do RF foi {latency_ratio:.1f} vezes maior. A diferença não deve ser extrapolada para ARM ou para uma rede UAV."""
        ),
        markdown("## Lotes, throughput e recursos"),
        code(
            """batches = pd.read_csv(report_dir / "batch_http_latency.csv")
print(batches.round(3).to_string(index=False))""",
            batches.round(3).to_string(index=False),
            3,
        ),
        code(
            """throughput = pd.read_csv(report_dir / "throughput.csv")
resources = pd.read_csv(report_dir / "resource_usage.csv")
print(throughput.round(3).to_string(index=False))
print()
print(resources.round(3).to_string(index=False))""",
            throughput.round(3).to_string(index=False)
            + "\n\n"
            + resources.round(3).to_string(index=False),
            4,
        ),
        markdown(
            f"""O RF usou {memory_ratio:.1f} vezes mais memória máxima observada e seu artefato foi {size_ratio:.1f} vezes maior. Concorrência adicional não aumentou o throughput do RF sob a quota de meio núcleo; no XGBoost, a melhor média também ocorreu com concorrência 1. Isso descreve esta implementação com acesso serializado ao modelo, não uma propriedade universal dos algoritmos."""
        ),
        markdown("## Fronteira qualidade–custo"),
        code(
            """tradeoff = pd.read_csv(report_dir / "quality_cost_tradeoff.csv")
print(tradeoff.round(6).to_string(index=False))""",
            tradeoff.round(6).to_string(index=False),
            5,
        ),
        markdown(
            f"""Na rodada de estabilidade S2, a diferença média de F1-macro XGBoost − RF foi **{f1_difference:+.6f}**, pequena diante da variação entre folds. No benchmark Docker, porém, XGBoost combinou latência, tamanho e memória muito menores. A conclusão defensável é uma vantagem operacional do XGBoost nesta bancada, e não superioridade preditiva universal.

As métricas de qualidade vêm das predições OOF de S2. Os artefatos Docker foram reajustados em todos os dados somente para medição de sistemas e não recebem um novo escore preditivo nos dados de ajuste."""
        ),
        markdown(
            """## Limites

O benchmark atende vetores de fluxo já calculados em loopback Docker Desktop/WSL2. Ele não inclui extração causal dos atributos, rádio, mobilidade, perda de rede, energia, bateria, hardware ARM ou tempo até detecção. Os limites de 0,5 CPU e 512 MiB são controles de cgroup, não uma simulação fiel de Raspberry Pi, Jetson ou drone físico."""
        ),
    ]
    notebook = {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3 (.venv)",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3.12.10"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    NOTEBOOK_PATH.write_text(
        json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(NOTEBOOK_PATH)


if __name__ == "__main__":
    main()
