"""Generate publication-exportable figures only from a verified paired analysis."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.uavids_study.predictive_experiment import file_hash, write_json


def build(config_path):
    config = json.loads(Path(config_path).read_text("utf-8"))
    report = ROOT / "reports" / config["experiment_id"]
    manifest = json.loads((report / "analysis_manifest.json").read_text("utf-8"))
    if not manifest["requested_protocols_complete"]:
        raise ValueError("Cannot build a report from incomplete OOF predictions")
    for name, checksum in manifest["output_sha256"].items():
        path = (report / name).resolve()
        if not path.is_relative_to(report.resolve()) or file_hash(path) != checksum:
            raise ValueError(f"Analysis output changed: {name}")
    pooled = pd.read_csv(report / "pooled_metrics.csv")
    comparisons = pd.read_csv(report / "paired_comparisons.csv")
    classes = pd.read_csv(report / "class_metrics.csv")
    figures = report / "figures"
    figures.mkdir(exist_ok=True)
    generated = {}
    plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
    for (protocol, seed), group in comparisons.groupby(["protocol", "seed"]):
        group = group.sort_values(["model", "condition"]).reset_index(drop=True)
        fig, ax = plt.subplots(figsize=(7.2, max(3, .45 * len(group))))
        for index, row in group.iterrows():
            color = "#006d77" if row.model == "xgboost" else "#a44200"
            ax.hlines(index, row.ci_low * 100, row.ci_high * 100, color=color, linewidth=2)
            ax.scatter(row.f1_macro_delta * 100, index, color=color, s=28, zorder=3)
        ax.axvline(0, color="0.4", linestyle="--", linewidth=1)
        ax.set_yticks(range(len(group)), [f"{row.model} / {row.condition}" for row in group.itertuples()])
        ax.invert_yaxis()
        ax.set_xlabel("Difference in macro-F1 versus A0 (percentage points)")
        ax.set_title(f"{protocol} · seed {seed} · conditional group bootstrap")
        ax.grid(axis="x", alpha=.2)
        fig.tight_layout()
        for extension in ("pdf", "svg", "png"):
            path = figures / f"paired_{protocol.lower()}__seed_{seed}.{extension}"
            fig.savefig(path, dpi=220, bbox_inches="tight")
            generated[path.relative_to(report).as_posix()] = file_hash(path)
        plt.close(fig)
    for (protocol, seed, model), group in classes.groupby(["protocol", "seed", "model"]):
        matrix = group.pivot(index="class_name", columns="condition", values="f1").reindex(
            index=config["class_order"], columns=list(config["conditions"]))
        fig, ax = plt.subplots(figsize=(6.3, 3.6))
        im = ax.imshow(matrix, vmin=0, vmax=1, cmap="Blues", aspect="auto")
        ax.set_xticks(range(len(matrix.columns)), matrix.columns)
        ax.set_yticks(range(len(matrix.index)), [label.replace(" Attack", "").replace(" Traffic", "") for label in matrix.index])
        for row in range(len(matrix.index)):
            for col in range(len(matrix.columns)):
                value = matrix.iloc[row, col]
                ax.text(col, row, f"{value:.3f}", ha="center", va="center", color="white" if value > .6 else "black")
        ax.set_title(f"OOF class F1 · {protocol} · {model} · seed {seed}")
        fig.colorbar(im, ax=ax, label="F1")
        fig.tight_layout()
        for extension in ("pdf", "svg", "png"):
            path = figures / f"class_f1_{protocol.lower()}__{model}__seed_{seed}.{extension}"
            fig.savefig(path, dpi=220, bbox_inches="tight")
            generated[path.relative_to(report).as_posix()] = file_hash(path)
        plt.close(fig)
    lines = ["# Relatório exploratório de ablação", "",
        f"Experimento: `{config['experiment_id']}`. Protocolos completos desta análise: {', '.join(manifest['protocols'])}.", "",
        f"Painel integral completo: **{manifest['whole_experiment_complete']}**. Consultar o manifesto para cobertura e hashes.", "",
        "F1 OOF usa todos os exemplos uma única vez; a média dos folds é descritiva e tem outra ponderação.", "",
        "| Protocolo | Modelo | Seed | Condição | F1 OOF | Média dos folds |", "|---|---|---|---|---|---|"]
    for row in pooled.itertuples():
        lines.append(f"| {row.protocol} | {row.model} | {row.seed} | {row.condition} | {row.f1_macro:.6f} | {row.fold_f1_mean:.6f} |")
    lines.extend(["", "## Interpretação e rastreabilidade", "",
        "Intervalos em `paired_comparisons.csv` são pareados, por grupos e condicionais às predições OOF fixas. Não medem toda a incerteza de retreinamento. Seeds não são replicações independentes; intervalos são exploratórios e sem ajuste de multiplicidade.", "",
        "`class_metrics.csv` contém precisão, recall, F1 e suporte; `confusion_counts.csv` permite examinar ataque→normal e confusões Blackhole/Wormhole. Resultados negativos permanecem nas tabelas.", "",
        "A auditoria de derivadas está em `research_artifacts/derived_features/`. Redundância algébrica não constitui novidade nem ganho causal. Os gráficos usam limites fixos de F1 entre 0 e 1.", "",
        "Tempos de ajuste e inferência em `results/<experiment_id>/fold_metrics.csv` descrevem estas execuções, sem equivalência com hardware embarcado ou energia.", "",
        "O manuscrito deve distinguir os resultados deste painel das rodadas históricas e comparar apenas tarefas/protocolos compatíveis na literatura."])
    if "protocol_comparisons.csv" in manifest["output_sha256"]:
        lines.extend(["", "`protocol_comparisons.csv` compara os protocolos nas mesmas linhas com bootstrap por SrcAddr. É sensibilidade descritiva: regimes de treino e padrões de vazamento variam; diferenças não isolam uma causa."])
    if "seed_variation.csv" in manifest["output_sha256"]:
        lines.extend(["", "`seed_variation.csv` resume média, desvio padrão descritivo e amplitude entre seeds para F1 e diferenças. Seeds não são populações independentes nem base para teste t."])
    parity = report / "control_parity_manifest.json"
    if parity.exists():
        checked = json.loads(parity.read_text("utf-8"))
        if file_hash(report / "control_parity.csv") != checked["table_sha256"]:
            raise ValueError("Control parity table changed")
        lines.extend(["", f"Controle A0 versus baseline histórica: {checked['exact_equal_jobs']}/{checked['jobs']} jobs com predições e probabilidades exatamente iguais. Consulte `control_parity.csv` e seu manifesto."])
    path = report / "REPORT.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    generated[path.name] = file_hash(path)
    write_json(report / "report_manifest.json", {"experiment_id": config["experiment_id"],
        "analysis_manifest_sha256": file_hash(report / "analysis_manifest.json"),
        "generator_sha256": file_hash(Path(__file__)), "output_sha256": generated})
    print(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/feature_ablation_v4.json")
    build(parser.parse_args().config)
