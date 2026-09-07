"""Build stability analysis for fixed S2 models across three seeds."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = PROJECT_ROOT / "results" / "stability_s2_v3"
REPORT_DIR = PROJECT_ROOT / "reports" / "stability_s2_v3"
NOTEBOOK_PATH = PROJECT_ROOT / "notebooks" / "research" / "03_estabilidade_sementes_s2.ipynb"


def markdown_cell(source: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": source.splitlines(True)}


def code_cell(source: str, output: str, execution_count: int) -> dict:
    return {
        "cell_type": "code",
        "execution_count": execution_count,
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
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((RESULT_DIR / "experiment_manifest.json").read_text("utf-8"))
    metrics = pd.read_csv(RESULT_DIR / "metrics_by_fold.csv")
    pooled = pd.read_csv(RESULT_DIR / "metrics_pooled_oof.csv")

    fold_seed = (
        metrics.groupby(["model", "fold"])["f1_macro"]
        .agg(seed_mean="mean", seed_std="std", seed_min="min", seed_max="max")
        .reset_index()
    )
    decomposition_rows = []
    for model, selected in fold_seed.groupby("model"):
        decomposition_rows.append(
            {
                "model": model,
                "overall_fold_seed_mean": metrics.loc[
                    metrics["model"] == model, "f1_macro"
                ].mean(),
                "mean_within_fold_seed_std": selected["seed_std"].mean(),
                "maximum_within_fold_seed_std": selected["seed_std"].max(),
                "between_fold_std_of_seed_means": selected["seed_mean"].std(ddof=1),
                "between_fold_range_of_seed_means": selected["seed_mean"].max()
                - selected["seed_mean"].min(),
            }
        )
    decomposition = pd.DataFrame(decomposition_rows)
    decomposition.to_csv(
        REPORT_DIR / "variance_decomposition.csv", index=False, lineterminator="\n"
    )
    fold_seed.to_csv(REPORT_DIR / "fold_seed_stability.csv", index=False, lineterminator="\n")

    paired = metrics.pivot(
        index=["fold", "seed"], columns="model", values="f1_macro"
    ).reset_index()
    paired["xgboost_minus_random_forest"] = (
        paired["xgboost"] - paired["random_forest"]
    )
    paired.to_csv(REPORT_DIR / "paired_model_differences.csv", index=False, lineterminator="\n")

    pooled_view = pooled[
        [
            "model",
            "seed",
            "f1_macro",
            "accuracy",
            "log_loss",
            "false_alarm_rate",
            "missed_attack_rate",
        ]
    ].sort_values(["model", "seed"])
    pooled_view.to_csv(REPORT_DIR / "pooled_metrics_by_seed.csv", index=False, lineterminator="\n")

    fig, axis = plt.subplots(figsize=(9, 5.5))
    colors = {"random_forest": "#4C78A8", "xgboost": "#F58518"}
    labels = {"random_forest": "Random Forest", "xgboost": "XGBoost"}
    for model, selected in metrics.groupby("model"):
        for seed, seed_rows in selected.groupby("seed"):
            seed_rows = seed_rows.sort_values("fold")
            axis.plot(
                seed_rows["fold"],
                seed_rows["f1_macro"],
                color=colors[model],
                alpha=0.22,
                linewidth=1,
            )
        means = selected.groupby("fold")["f1_macro"].mean()
        axis.plot(
            means.index,
            means.values,
            marker="o",
            linewidth=2.4,
            color=colors[model],
            label=labels[model],
        )
    axis.set_xticks(range(5))
    axis.set_xlabel("Fold externo S2")
    axis.set_ylabel("F1 macro")
    axis.set_title("Variação entre folds e sementes de ajuste")
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "fold_and_seed_variation.png", dpi=180)
    plt.close(fig)

    rf = decomposition.query("model == 'random_forest'").iloc[0]
    xgb = decomposition.query("model == 'xgboost'").iloc[0]
    paired_mean = paired["xgboost_minus_random_forest"].mean()
    paired_std = paired["xgboost_minus_random_forest"].std(ddof=1)
    xgb_wins = int((paired["xgboost_minus_random_forest"] > 0).sum())

    report = f"""# Estabilidade por sementes em S2

- Jobs: {manifest['completed_jobs']}/{manifest['expected_jobs']}.
- Modelos: Random Forest e XGBoost com parâmetros fixos.
- Sementes: 3; folds de origem: 5; predições OOF completas por modelo/semente.

## Variação observada

- Random Forest: desvio médio entre sementes dentro do mesmo fold {rf.mean_within_fold_seed_std:.6f}; desvio entre as médias dos folds {rf.between_fold_std_of_seed_means:.6f}.
- XGBoost: desvio médio entre sementes dentro do mesmo fold {xgb.mean_within_fold_seed_std:.6f}; desvio entre as médias dos folds {xgb.between_fold_std_of_seed_means:.6f}.
- Diferença pareada XGBoost − RF: média {paired_mean:+.6f}, desvio {paired_std:.6f}; XGBoost venceu {xgb_wins}/15 pares fold/semente.

A composição dos grupos de origem produz variação muito maior que a semente de ajuste. A vantagem média do XGBoost é pequena e não ocorre em todos os folds. XGBoost permanece candidato principal por combinar F1 ligeiramente maior, menos falsos alarmes e artefato muito menor no baseline; RF permanece comparador necessário.

As sementes compartilham os mesmos dados e não são réplicas independentes. Esta análise não substitui novas simulações nem validação externa.
"""
    (REPORT_DIR / "README.md").write_text(report, encoding="utf-8")

    cells = [
        markdown_cell(
            """# UAVIDS-2025 — estabilidade por sementes em S2

Esta rodada mantém dados, folds, atributos e hiperparâmetros fixos e varia somente a semente de ajuste. O objetivo é verificar se a incerteza algorítmica é relevante diante da heterogeneidade entre grupos de origem.
"""
        ),
        markdown_cell(
            """## Protocolo

Foram usadas três sementes para XGBoost e Random Forest nos cinco folds externos S2. As configurações vieram da rodada aninhada v2 e estão congeladas em [`stability_s2_v3.json`](../../configs/stability_s2_v3.json). As sementes são repetições do algoritmo, não novos datasets.
"""
        ),
        code_cell(
            """from pathlib import Path
import json
import pandas as pd

project_root = Path.cwd().resolve()
if project_root.name == "research":
    project_root = project_root.parents[1]
elif project_root.name == "notebooks":
    project_root = project_root.parent

result_dir = project_root / "results" / "stability_s2_v3"
report_dir = project_root / "reports" / "stability_s2_v3"
manifest = json.loads((result_dir / "experiment_manifest.json").read_text("utf-8"))
print(json.dumps(manifest, indent=2, ensure_ascii=False))
""",
            json.dumps(manifest, indent=2, ensure_ascii=False),
            1,
        ),
        markdown_cell("## Métricas OOF por semente"),
        code_cell(
            """pooled_metrics = pd.read_csv(report_dir / "pooled_metrics_by_seed.csv")
print(pooled_metrics.round(6).to_string(index=False))
""",
            pooled_view.round(6).to_string(index=False),
            2,
        ),
        markdown_cell(
            """## Decomposição descritiva da variação

O desvio entre sementes é calculado dentro de cada fold. O desvio entre folds usa a média das três sementes de cada fold. Essa separação evita misturar duas fontes de variação com interpretações diferentes.
"""
        ),
        code_cell(
            """variance = pd.read_csv(report_dir / "variance_decomposition.csv")
print(variance.round(6).to_string(index=False))
""",
            decomposition.round(6).to_string(index=False),
            3,
        ),
        markdown_cell("![Variação entre folds e sementes](../../reports/stability_s2_v3/fold_and_seed_variation.png)"),
        markdown_cell("## Diferença pareada entre modelos"),
        code_cell(
            """paired = pd.read_csv(report_dir / "paired_model_differences.csv")
print(paired.round(6).to_string(index=False))
""",
            paired.round(6).to_string(index=False),
            4,
        ),
        markdown_cell(
            f"""## Interpretação

- O desvio médio entre sementes foi **{rf.mean_within_fold_seed_std:.6f}** para RF e **{xgb.mean_within_fold_seed_std:.6f}** para XGBoost.
- O desvio entre folds foi **{rf.between_fold_std_of_seed_means:.6f}** para RF e **{xgb.between_fold_std_of_seed_means:.6f}** para XGBoost.
- XGBoost superou RF em **{xgb_wins}/15** pares, com diferença média **{paired_mean:+.6f}**.

A origem mantida fora do treino explica mais variação que a semente. A evidência não sustenta dizer que XGBoost domina RF em qualquer origem; sustenta apenas uma vantagem média pequena nesta população S2, combinada a menor tamanho serializado e menor taxa de falso alarme.

O próximo passo operacional pode congelar ambos os modelos e medir batch 1, pipeline e requisição. Esses benchmarks não corrigirão a ausência de novas simulações externas.
"""
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
            "language_info": {
                "name": "python",
                "version": manifest["environment"]["python"],
            },
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
