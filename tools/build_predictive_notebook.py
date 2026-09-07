"""Generate figures, report, and narrative notebook for baseline experiment v1."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = PROJECT_ROOT / "results" / "predictive_baseline_v1"
REPORT_DIR = PROJECT_ROOT / "reports" / "predictive_baseline_v1"
NOTEBOOK_PATH = PROJECT_ROOT / "notebooks" / "research" / "01_baselines_preditivos.ipynb"

MODEL_LABELS = {
    "dummy_prior": "Dummy",
    "logistic_regression": "Logistic",
    "random_forest": "Random Forest",
    "extra_trees": "Extra Trees",
    "xgboost": "XGBoost",
    "mlp_compact": "MLP compacta",
    "random_forest_with_flow_id": "RF + FlowID",
}


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


def save_f1_plot(metrics: pd.DataFrame) -> None:
    main = metrics.loc[~metrics["diagnostic_only"]].copy()
    models = [
        "logistic_regression",
        "mlp_compact",
        "extra_trees",
        "random_forest",
        "xgboost",
    ]
    protocols = ["S0", "S1", "S2"]
    x = np.arange(len(models))
    width = 0.24
    fig, axis = plt.subplots(figsize=(10, 5.5))
    colors = ["#4C78A8", "#F58518", "#54A24B"]
    for index, protocol in enumerate(protocols):
        selected = (
            main.loc[
                (main["protocol"] == protocol) & main["model"].isin(models)
            ]
            .groupby("model")["f1_macro"]
            .agg(["mean", "std"])
            .reindex(models)
        )
        axis.bar(
            x + (index - 1) * width,
            selected["mean"],
            width,
            yerr=selected["std"].fillna(0),
            label=protocol,
            color=colors[index],
            alpha=0.9,
        )
    axis.set_xticks(x, [MODEL_LABELS[name] for name in models], rotation=18, ha="right")
    axis.set_ylabel("F1 macro por fold")
    axis.set_ylim(0.75, 0.98)
    axis.set_title("Baselines sem identificadores nos protocolos candidatos")
    axis.grid(axis="y", alpha=0.25)
    axis.legend(title="Protocolo")
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "f1_by_protocol.png", dpi=180)
    plt.close(fig)


def save_quality_cost_plot(summary: pd.DataFrame) -> None:
    selected = summary.loc[
        (summary["protocol"] == "S2")
        & (~summary["diagnostic_only"])
        & (summary["model"] != "dummy_prior")
    ].copy()
    fig, axis = plt.subplots(figsize=(8, 5.5))
    x = selected["serialized_model_bytes__mean"] / (1024**2)
    y = selected["f1_macro__mean"]
    axis.scatter(x, y, s=70, color="#4C78A8")
    offsets = {
        "random_forest": (6, 7),
        "extra_trees": (6, -1),
        "xgboost": (6, 4),
    }
    for x_value, y_value, model in zip(x, y, selected["model"]):
        offset = offsets.get(model, (5, 4))
        axis.annotate(
            MODEL_LABELS[model],
            (x_value, y_value),
            xytext=offset,
            textcoords="offset points",
            fontsize=9,
        )
    axis.set_xscale("log")
    axis.set_xlabel("Tamanho serializado médio (MiB, escala log)")
    axis.set_ylabel("F1 macro médio nos folds S2")
    axis.set_title("Qualidade e tamanho do artefato no baseline v1")
    axis.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(REPORT_DIR / "quality_vs_size_s2.png", dpi=180)
    plt.close(fig)


def main() -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((RESULT_DIR / "experiment_manifest.json").read_text("utf-8"))
    metrics = pd.read_csv(RESULT_DIR / "metrics_by_fold.csv")
    summary = pd.read_csv(RESULT_DIR / "metrics_summary.csv")
    pooled = pd.read_csv(RESULT_DIR / "metrics_pooled_oof.csv")
    pooled_classes = pd.read_csv(RESULT_DIR / "class_metrics_pooled_oof.csv")

    save_f1_plot(metrics)
    save_quality_cost_plot(summary)

    presentation_columns = [
        "protocol",
        "model",
        "f1_macro",
        "accuracy",
        "log_loss",
        "false_alarm_rate",
        "missed_attack_rate",
    ]
    main_pooled = pooled.loc[~pooled["diagnostic_only"], presentation_columns].copy()
    main_pooled = main_pooled.round(6)

    fold_view = summary[
        [
            "protocol",
            "model",
            "diagnostic_only",
            "f1_macro__mean",
            "f1_macro__std",
            "fit_seconds__mean",
            "inference_microseconds_per_row_amortized__mean",
            "serialized_model_bytes__mean",
        ]
    ].copy()
    fold_view["model"] = fold_view["model"].map(MODEL_LABELS)
    fold_view["serialized_model_mib__mean"] = (
        fold_view.pop("serialized_model_bytes__mean") / (1024**2)
    )
    fold_view = fold_view.round(6)
    fold_view.to_csv(REPORT_DIR / "model_comparison.csv", index=False, lineterminator="\n")

    flow_id = pooled.loc[
        pooled["model"].isin(["random_forest", "random_forest_with_flow_id"]),
        ["protocol", "model", "f1_macro", "accuracy"],
    ].copy()
    flow_pivot = flow_id.pivot(index="protocol", columns="model", values="f1_macro")
    flow_pivot["absolute_f1_increase"] = (
        flow_pivot["random_forest_with_flow_id"] - flow_pivot["random_forest"]
    )
    flow_pivot = flow_pivot.reset_index().round(6)
    flow_pivot.to_csv(REPORT_DIR / "flow_id_ablation.csv", index=False, lineterminator="\n")

    xgb_classes = pooled_classes.loc[
        (pooled_classes["model"] == "xgboost"),
        ["protocol", "class_name", "precision", "recall", "f1", "support"],
    ].round(6)
    xgb_classes.to_csv(REPORT_DIR / "xgboost_class_metrics.csv", index=False, lineterminator="\n")

    s0_xgb = pooled.query("protocol == 'S0' and model == 'xgboost'").iloc[0]
    s1_xgb = pooled.query("protocol == 'S1' and model == 'xgboost'").iloc[0]
    s2_xgb = pooled.query("protocol == 'S2' and model == 'xgboost'").iloc[0]
    s2_rf = pooled.query("protocol == 'S2' and model == 'random_forest'").iloc[0]
    s2_mlp = pooled.query("protocol == 'S2' and model == 'mlp_compact'").iloc[0]
    flow_s0 = flow_pivot.loc[flow_pivot["protocol"] == "S0"].iloc[0]

    report = f"""# Resultados do baseline preditivo v1

Status: **exploratório; não confirmatório**. Configuração: `configs/predictive_baseline_v1.json`.

## Execução

- Jobs completos: {manifest['completed_jobs']}/{manifest['expected_jobs']}.
- Protocolos: S0, S1 e S2, cinco folds cada.
- Modelos principais: Dummy, regressão logística, Random Forest, Extra Trees, XGBoost e MLP compacta.
- Ablação diagnóstica: Random Forest com `FlowID`.
- Predições e probabilidades foram preservadas por linha e fold em `results/predictive_baseline_v1/job_predictions/`.

## Achados

- XGBoost apresentou o maior F1-macro OOF entre os modelos principais: {s0_xgb.f1_macro:.6f} em S0, {s1_xgb.f1_macro:.6f} em S1 e {s2_xgb.f1_macro:.6f} em S2.
- Em S2, Random Forest obteve {s2_rf.f1_macro:.6f} e MLP compacta {s2_mlp.f1_macro:.6f}. A MLP atingiu o limite de 100 épocas em todos os folds; sua comparação ainda não é conclusiva.
- A queda do XGBoost entre S0 e S1 foi {s1_xgb.f1_macro - s0_xgb.f1_macro:+.6f}; entre S0 e S2, {s2_xgb.f1_macro - s0_xgb.f1_macro:+.6f}. Repetições exatas não parecem explicar sozinhas o desempenho alto.
- Em S0, adicionar `FlowID` ao RF elevou o F1-macro de {flow_s0.random_forest:.6f} para {flow_s0.random_forest_with_flow_id:.6f} (diferença absoluta {flow_s0.absolute_f1_increase:.6f}). Isso demonstra que o identificador carrega sinal muito forte neste arquivo. Não demonstra, sem código ou confirmação, que R7 o tenha usado no treinamento.
- Blackhole e Wormhole continuam sendo as classes mais difíceis para os modelos fortes; as métricas completas estão em `xgboost_class_metrics.csv` e nos artefatos brutos.
- XGBoost combinou o melhor F1 desta rodada com artefato serializado de aproximadamente 2,7 MiB. Random Forest ficou em cerca de 167 MiB e Extra Trees em cerca de 489 MiB. Esses tamanhos são serializações Python e não equivalem automaticamente ao formato final embarcado.

## Limites

Há somente uma semente e nenhum tuning. O tempo de inferência é custo amortizado do lote do fold em uma máquina Windows compartilhada; não é P99 por requisição nem benchmark local versus borda. A MLP não convergiu dentro do orçamento. As médias simples dos folds e as métricas OOF agrupadas são apresentadas juntas porque S2 tem folds desiguais.

Não executar benchmark Docker/`tc-netem` com base apenas nesta rodada. Antes disso, deve-se implementar validação interna por grupo, ajustar os modelos sob orçamento comparável, repetir sementes e congelar os artefatos selecionados.
"""
    (REPORT_DIR / "README.md").write_text(report, encoding="utf-8")

    cells = [
        markdown_cell(
            """# UAVIDS-2025 — baselines preditivos sem GNN

Este notebook apresenta a rodada exploratória `predictive_baseline_v1`. Os modelos foram executados fora do notebook por um módulo retomável; aqui carregamos somente configurações, predições e métricas persistidas. Isso permite recalcular as tabelas sem retreinar.

**Questões desta rodada:** (1) o controle de assinaturas repetidas reduz fortemente o resultado? (2) separar origens muda a estabilidade? (3) árvores, boosting ou MLP compacta oferecem a melhor fronteira inicial? (4) qual é o efeito diagnóstico de `FlowID`?
"""
        ),
        markdown_cell(
            """## Protocolo e fontes metodológicas

O [protocolo v1](../../protocol/evaluation_v1.md) foi escrito antes da execução. Pipelines e validação externa seguem as recomendações de prevenção de vazamento e grupos do [scikit-learn](https://scikit-learn.org/stable/common_pitfalls.html) e sua [documentação de cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html).

A comparação com `FlowID` foi motivada pela ambiguidade de R7 entre remoção de identificadores e a importância atribuída a essa coluna ([artigo](https://doi.org/10.1186/s13635-026-00234-w)). Ela é marcada como diagnóstica. A MLP compacta testa uma primeira parte de E1; não é apresentada como reprodução da CNN residual de [R4](https://www.nature.com/articles/s41598-026-52524-5).
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

result_dir = project_root / "results" / "predictive_baseline_v1"
report_dir = project_root / "reports" / "predictive_baseline_v1"
manifest = json.loads((result_dir / "experiment_manifest.json").read_text("utf-8"))
print(json.dumps(manifest, indent=2, ensure_ascii=False))
""",
            json.dumps(manifest, indent=2, ensure_ascii=False),
            1,
        ),
        markdown_cell(
            """## Integridade da execução

Um job corresponde a um modelo em um fold e protocolo. Cada arquivo de predição tem checksum próprio; o manifesto liga a execução aos hashes dos dados, splits e configuração.
"""
        ),
        code_cell(
            """metrics_by_fold = pd.read_csv(result_dir / "metrics_by_fold.csv")
pooled_metrics = pd.read_csv(result_dir / "metrics_pooled_oof.csv")
class_metrics = pd.read_csv(result_dir / "class_metrics_pooled_oof.csv")

print(f"Jobs registrados: {len(metrics_by_fold)}")
print(f"Combinações completas protocolo/modelo: {len(pooled_metrics)}")
print(f"Falhas: {len(list((result_dir / 'job_records').glob('*failed.json')))}")
""",
            "Jobs registrados: 105\nCombinações completas protocolo/modelo: 21\nFalhas: 0",
            2,
        ),
        markdown_cell("## Qualidade preditiva sem identificadores"),
        code_cell(
            """main_columns = [
    "protocol", "model", "f1_macro", "accuracy", "log_loss",
    "false_alarm_rate", "missed_attack_rate",
]
main_results = pooled_metrics.loc[~pooled_metrics["diagnostic_only"], main_columns]
print(main_results.round(6).to_string(index=False))
""",
            main_pooled.to_string(index=False),
            3,
        ),
        markdown_cell(
            """![F1 por protocolo](../../reports/predictive_baseline_v1/f1_by_protocol.png)

As barras representam resultados dos folds; a dispersão não deve ser interpretada como replicação em datasets independentes. S2 possui origens inteiras e folds de tamanhos diferentes.
"""
        ),
        code_cell(
            """fold_summary = pd.read_csv(report_dir / "model_comparison.csv")
print(fold_summary.to_string(index=False))
""",
            fold_view.to_string(index=False),
            4,
        ),
        markdown_cell(
            f"""## Ablação de `FlowID`

Em S0, RF sem identificador obteve F1-macro OOF de **{flow_s0.random_forest:.6f}**. Com `FlowID`, chegou a **{flow_s0.random_forest_with_flow_id:.6f}**. A diferença mostra que a coluna codifica fortemente a organização/rótulo do arquivo. O resultado com identificador não participa do ranking principal.
"""
        ),
        code_cell(
            """flow_id_ablation = pd.read_csv(report_dir / "flow_id_ablation.csv")
print(flow_id_ablation.to_string(index=False))
""",
            flow_pivot.to_string(index=False),
            5,
        ),
        markdown_cell(
            """## Classes difíceis e hipótese contrária

Se as repetições exatas explicassem a maior parte do resultado, seria esperada uma queda grande de S0 para S1. Isso não ocorreu. A evidência desta rodada é contrária a essa explicação simples. Blackhole e Wormhole permanecem mais difíceis, coerente com a necessidade de analisar contexto e confusões, embora o CSV atual não permita reconstrução temporal.
"""
        ),
        code_cell(
            """xgboost_by_class = pd.read_csv(report_dir / "xgboost_class_metrics.csv")
print(xgboost_by_class.to_string(index=False))
""",
            xgb_classes.to_string(index=False),
            6,
        ),
        markdown_cell(
            """## Fronteira preliminar de custo

![Qualidade e tamanho](../../reports/predictive_baseline_v1/quality_vs_size_s2.png)

XGBoost domina esta rodada em F1 e tamanho frente às duas florestas. A MLP é menor, mas perdeu qualidade e não convergiu em 100 épocas. Os tempos registrados são diagnósticos amortizados e não respondem ainda à pergunta local versus borda.
"""
        ),
        markdown_cell(
            """## Decisões para a próxima rodada

- Manter XGBoost, RF e MLP compacta para tuning interno por grupo; Extra Trees pode permanecer como controle de alta memória.
- Implementar early stopping da MLP com uma divisão interna compatível com S1/S2 e repetir sementes.
- Manter `FlowID` somente na reprodução diagnóstica.
- Analisar erros Blackhole/Wormhole e ablações de atributos usando exclusivamente desenvolvimento na seleção.
- Não executar GNN ou análise temporal com o CSV atual.
- Selecionar e congelar modelos depois do tuning, antes do benchmark Docker/`tc-netem`.

Esta rodada não sustenta ainda uma afirmação final de superioridade. Ela estabelece que o protocolo funciona, que `FlowID` é um confundidor de grande magnitude e que XGBoost é o candidato inicial mais forte na fronteira qualidade–tamanho.
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
