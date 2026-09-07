"""Build the report and notebook for exploratory nested tuning v2."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASELINE_DIR = PROJECT_ROOT / "results" / "predictive_baseline_v1"
TUNING_DIR = PROJECT_ROOT / "results" / "nested_tuning_v2"
REPORT_DIR = PROJECT_ROOT / "reports" / "nested_tuning_v2"
NOTEBOOK_PATH = PROJECT_ROOT / "notebooks" / "research" / "02_tuning_aninhado_s2.ipynb"


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


def load_job_records() -> list[dict]:
    records = []
    for path in sorted((TUNING_DIR / "job_records").glob("*.json")):
        record = json.loads(path.read_text(encoding="utf-8"))
        if record.get("status") == "complete":
            records.append(record)
    return records


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((TUNING_DIR / "experiment_manifest.json").read_text("utf-8"))
    tuning_metrics = pd.read_csv(TUNING_DIR / "metrics_by_fold.csv")
    baseline_metrics = pd.read_csv(BASELINE_DIR / "metrics_by_fold.csv")
    baseline_metrics = baseline_metrics.loc[
        (baseline_metrics["protocol"] == "S2")
        & baseline_metrics["model"].isin(["random_forest", "xgboost"]),
        ["fold", "model", "f1_macro"],
    ].rename(columns={"f1_macro": "baseline_f1_macro"})
    comparison = tuning_metrics[
        ["fold", "model", "f1_macro", "fit_seconds", "serialized_model_bytes"]
    ].rename(columns={"f1_macro": "tuned_f1_macro"})
    comparison = comparison.merge(baseline_metrics, on=["fold", "model"])
    comparison["f1_difference"] = (
        comparison["tuned_f1_macro"] - comparison["baseline_f1_macro"]
    )
    comparison = comparison.sort_values(["model", "fold"])
    comparison.to_csv(REPORT_DIR / "baseline_vs_tuning.csv", index=False, lineterminator="\n")

    records = load_job_records()
    selection_rows = []
    candidate_rows = []
    for record in records:
        selection_rows.append(
            {
                "fold": record["fold"],
                "model": record["model"],
                "selected_candidate_id": record["selected_candidate_id"],
                "inner_selection_f1_macro": record["inner_selection_score"],
                "outer_f1_macro": record["metrics"]["f1_macro"],
                "tuning_fit_count": record["tuning_fit_count"],
                "tuning_seconds": record["tuning_seconds"],
                "final_fit_seconds": record["fit_seconds"],
                "warning_count": len(record["warnings"]),
            }
        )
        for candidate in record["candidate_results"]:
            candidate_rows.append(
                {
                    "fold": record["fold"],
                    "model": record["model"],
                    "candidate_id": candidate["candidate_id"],
                    "complexity_rank": candidate["complexity_rank"],
                    "mean_inner_f1_macro": candidate["mean_inner_f1_macro"],
                    "std_inner_f1_macro": candidate["std_inner_f1_macro"],
                    "selected": candidate["candidate_id"]
                    == record["selected_candidate_id"],
                }
            )
    selections = pd.DataFrame(selection_rows).sort_values(["model", "fold"])
    candidates = pd.DataFrame(candidate_rows).sort_values(
        ["model", "fold", "candidate_id"]
    )
    selections.to_csv(REPORT_DIR / "selections_by_fold.csv", index=False, lineterminator="\n")
    candidates.to_csv(REPORT_DIR / "inner_candidate_scores.csv", index=False, lineterminator="\n")

    difference_summary = comparison.groupby("model")[
        ["baseline_f1_macro", "tuned_f1_macro", "f1_difference"]
    ].agg(["mean", "std", "min", "max"])
    difference_summary.columns = [
        f"{metric}__{stat}" for metric, stat in difference_summary.columns
    ]
    difference_summary = difference_summary.reset_index()
    difference_summary.to_csv(
        REPORT_DIR / "tuning_effect_summary.csv", index=False, lineterminator="\n"
    )

    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), sharey=True)
    for axis, model in zip(axes, ["random_forest", "xgboost"]):
        selected = comparison.loc[comparison["model"] == model]
        axis.axhline(0, color="black", linewidth=0.8)
        colors = ["#54A24B" if value >= 0 else "#E45756" for value in selected["f1_difference"]]
        axis.bar(selected["fold"].astype(str), selected["f1_difference"], color=colors)
        axis.set_title("Random Forest" if model == "random_forest" else "XGBoost")
        axis.set_xlabel("Fold externo S2")
        axis.grid(axis="y", alpha=0.25)
    axes[0].set_ylabel("F1 ajustado − F1 baseline")
    fig.suptitle("Efeito pareado do tuning aninhado")
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "paired_tuning_effect.png", dpi=180)
    plt.close(fig)

    rf_effect = difference_summary.query("model == 'random_forest'").iloc[0]
    xgb_effect = difference_summary.query("model == 'xgboost'").iloc[0]
    selection_counts = (
        selections.groupby(["model", "selected_candidate_id"])
        .size()
        .rename("folds_selected")
        .reset_index()
    )
    total_tuning_seconds = selections["tuning_seconds"].sum()
    total_fits = int(selections["tuning_fit_count"].sum() + len(selections))

    report = f"""# Tuning aninhado S2 — resultados exploratórios

- Jobs externos: {manifest['completed_jobs']}/{manifest['expected_jobs']}.
- Ajustes totais: {total_fits} (90 internos e 10 finais).
- Tempo acumulado das buscas internas: {total_tuning_seconds:.1f} s.
- Falhas/avisos: 0/0.

## Efeito do tuning

- Random Forest: diferença média pareada de F1-macro {rf_effect.f1_difference__mean:+.6f}, desvio entre folds {rf_effect.f1_difference__std:.6f}.
- XGBoost: diferença média pareada de F1-macro {xgb_effect.f1_difference__mean:+.6f}, desvio entre folds {xgb_effect.f1_difference__std:.6f}.
- O candidato XGBoost base foi escolhido nos cinco folds. O RF com 240 árvores e folha mínima 2 foi escolhido em quatro folds; o RF menor venceu o fold restante pelo critério registrado.

O espaço pequeno não trouxe ganho material ao XGBoost e trouxe ganho inferior a 0,001 ao RF. Esse resultado não justifica ampliar o espaço depois de consultar os testes externos. O baseline XGBoost continua sendo a configuração mais simples para a próxima etapa; o RF ajustado permanece comparador.

## Limites

A família e o protocolo S2 foram priorizados depois do baseline v1, então a rodada continua exploratória. Há uma semente. Os folds representam grupos de endereço, não datasets independentes nem UAVs físicos comprovados. Diferenças e desvios são descritivos; nenhum teste de significância com cinco folds será apresentado como evidência forte.
"""
    (REPORT_DIR / "README.md").write_text(report, encoding="utf-8")

    comparison_display = comparison[
        ["fold", "model", "baseline_f1_macro", "tuned_f1_macro", "f1_difference"]
    ].round(6)
    selection_display = selections.round(6)
    candidate_display = candidates.round(6)
    summary_display = difference_summary.round(6)

    cells = [
        markdown_cell(
            """# UAVIDS-2025 — tuning aninhado em S2

Esta rodada testa se um espaço pequeno e congelado de hiperparâmetros melhora Random Forest e XGBoost quando cada escolha é feita somente em validação interna por grupos de origem. O teste externo de cada fold não participa da escolha.

O estudo permanece exploratório porque as famílias foram priorizadas após observar `predictive_baseline_v1`.
"""
        ),
        markdown_cell(
            """## Método

O [protocolo v2](../../protocol/nested_tuning_v2.md) e a [configuração](../../configs/nested_tuning_v2.json) definem três candidatos por família, três folds internos `StratifiedGroupKFold`, F1-macro como critério e desempate por complexidade. Em cada fold externo, nove modelos são ajustados internamente e o candidato escolhido é reajustado no treino externo completo.
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

result_dir = project_root / "results" / "nested_tuning_v2"
report_dir = project_root / "reports" / "nested_tuning_v2"
manifest = json.loads((result_dir / "experiment_manifest.json").read_text("utf-8"))
print(json.dumps(manifest, indent=2, ensure_ascii=False))
""",
            json.dumps(manifest, indent=2, ensure_ascii=False),
            1,
        ),
        markdown_cell("## Seleção interna e custo"),
        code_cell(
            """selections = pd.read_csv(report_dir / "selections_by_fold.csv")
print(selections.round(6).to_string(index=False))
""",
            selection_display.to_string(index=False),
            2,
        ),
        code_cell(
            """candidate_scores = pd.read_csv(report_dir / "inner_candidate_scores.csv")
print(candidate_scores.round(6).to_string(index=False))
""",
            candidate_display.to_string(index=False),
            3,
        ),
        markdown_cell(
            """## Comparação pareada com o baseline

Cada diferença abaixo usa o mesmo fold externo S2. Ela descreve o efeito observado do procedimento de tuning; os cinco folds não são tratados como cinco datasets independentes.
"""
        ),
        code_cell(
            """comparison = pd.read_csv(report_dir / "baseline_vs_tuning.csv")
columns = ["fold", "model", "baseline_f1_macro", "tuned_f1_macro", "f1_difference"]
print(comparison[columns].round(6).to_string(index=False))
""",
            comparison_display.to_string(index=False),
            4,
        ),
        markdown_cell("![Efeito pareado do tuning](../../reports/nested_tuning_v2/paired_tuning_effect.png)"),
        code_cell(
            """effect_summary = pd.read_csv(report_dir / "tuning_effect_summary.csv")
print(effect_summary.round(6).to_string(index=False))
""",
            summary_display.to_string(index=False),
            5,
        ),
        markdown_cell(
            f"""## Interpretação

- O RF melhorou em média **{rf_effect.f1_difference__mean:+.6f}** de F1-macro por fold.
- O XGBoost mudou **{xgb_effect.f1_difference__mean:+.6f}**, sem ganho prático.
- O candidato XGBoost base venceu internamente nos cinco folds. Isso indica que aumentar a complexidade dentro do espaço registrado não foi necessário.
- O RF mais regularizado venceu quatro folds, mas a melhora média ficou abaixo de 0,001.
- As diferenças entre folds são maiores que o ganho médio do tuning. A composição dos grupos de origem continua sendo a principal fonte visível de variação.

Não ampliaremos a busca com base nesses testes. Para o benchmark de sistemas, a configuração XGBoost base pode ser congelada como candidata principal e o RF ajustado como comparador. Antes de conclusões preditivas finais, ainda são necessárias múltiplas sementes e, idealmente, novas simulações externas.
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
