"""Generate publication-ready figures from the verified article inputs."""
from __future__ import annotations

import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "manuscript" / "figures"
LATENCY = ROOT / "reports" / "docker_latency_v4" / "quality_latency_comparison.csv"
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 10.5,
    "axes.labelsize": 11,
    "xtick.labelsize": 9.5,
    "ytick.labelsize": 9.5,
    "svg.fonttype": "none",
    "savefig.facecolor": "white",
    "figure.facecolor": "white",
})


def save(fig: plt.Figure, stem: str) -> None:
    fig.savefig(OUT / f"{stem}.png", dpi=360, bbox_inches="tight", facecolor="white")
    fig.savefig(OUT / f"{stem}.svg", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def rounded_box(ax, xy, width, height, text, *, edge="#18324B", fontsize=9.5,
                fill="white", weight="normal", radius=0.025, pad=0.012):
    box = FancyBboxPatch(
        xy, width, height,
        boxstyle=f"round,pad={pad},rounding_size={radius}",
        linewidth=1.25, edgecolor=edge, facecolor=fill,
    )
    ax.add_patch(box)
    ax.text(xy[0] + width / 2, xy[1] + height / 2, text,
            ha="center", va="center", fontsize=fontsize, color="#17212B",
            fontweight=weight, linespacing=1.2)


def methodology() -> None:
    fig, ax = plt.subplots(figsize=(6.5, 5.0))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Two separate lanes make clear that predictive validation and the
    # single-session systems benchmark answer different questions.
    lane_y, lane_h = 0.055, 0.89
    ax.add_patch(FancyBboxPatch((0.035, lane_y), 0.45, lane_h,
                                boxstyle="round,pad=0.008,rounding_size=0.018",
                                linewidth=1.0, edgecolor="#587C9B", facecolor="#F8FAFC"))
    ax.add_patch(FancyBboxPatch((0.515, lane_y), 0.45, lane_h,
                                boxstyle="round,pad=0.008,rounding_size=0.018",
                                linewidth=1.0, edgecolor="#8D6B42", facecolor="#FCFAF6"))
    ax.text(0.26, 0.875, "AVALIAÇÃO PREDITIVA", ha="center", va="center",
            fontsize=10, fontweight="bold", color="#18324B")
    ax.text(0.74, 0.875, "CUSTO DE INFERÊNCIA", ha="center", va="center",
            fontsize=10, fontweight="bold", color="#69491F")

    left_x, box_w, box_h = 0.075, 0.37, 0.145
    left_ys = [0.685, 0.485, 0.285, 0.085]
    left_text = [
        "Cinco folds pareados\nDivisão aleatória estratificada\nGrupos por assinatura exata\nGrupos por endereço de origem",
        "Atributos originais e razões derivadas\nimputação ajustada só no treino",
        "Random Forest e XGBoost\nparâmetros fixos",
        "Predições fora da amostra\nF1-macro e métricas por classe",
    ]
    for y, txt in zip(left_ys, left_text):
        rounded_box(ax, (left_x, y), box_w, box_h, txt, edge="#587C9B", fontsize=9.3,
                    fill="white", radius=0.012, pad=0.006)

    right_x, right_w = 0.555, 0.37
    right_ys = [0.685, 0.485, 0.285, 0.085]
    right_text = [
        "Quatro modelos medidos\nLogística · MLP · XGBoost · RF",
        "Container Docker limitado\n0,5 CPU · 512 MiB · 1 thread",
        "Uma sessão ordenada\n5.000 requisições por modelo",
        "Custo observado\nHTTP P50/P95/P99 e memória",
    ]
    for y, txt in zip(right_ys, right_text):
        rounded_box(ax, (right_x, y), right_w, box_h, txt, edge="#8D6B42", fontsize=9.3,
                    fill="white", radius=0.012, pad=0.006)

    fig.subplots_adjust(left=0.015, right=0.985, top=0.99, bottom=0.02)
    save(fig, "figura_1_metodologia")


def performance() -> None:
    with LATENCY.open(encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["latency_status"] == "complete"]
    expected = {"logistic_regression", "mlp_compact", "xgboost", "random_forest"}
    if {row["model"] for row in rows} != expected:
        raise ValueError("The latency CSV does not contain the four expected completed models")

    names = {
        "logistic_regression": "Regressão logística",
        "mlp_compact": "MLP compacta",
        "xgboost": "XGBoost",
        "random_forest": "Random Forest",
    }
    colors = {"P50": "#176B87", "P95": "#D17A22", "P99": "#6941A5"}
    markers = {"P50": "o", "P95": "s", "P99": "D"}
    fig, (quality, latency) = plt.subplots(
        1, 2, figsize=(6.5, 3.75), sharey=True,
        gridspec_kw={"width_ratios": [1.0, 1.35]},
    )
    y = list(range(len(rows)))
    labels = [names[row["model"]] for row in rows]

    quality.scatter([float(row["s2_oof_f1_macro"]) for row in rows], y,
                    s=64, marker="o", facecolor="#176B87", edgecolor="#102D3A",
                    linewidth=0.8, zorder=3)
    quality.set_yticks(y, labels)
    quality.invert_yaxis()
    # Show the observed quality range clearly; the caption states the axis limit.
    quality.set_xlim(0.78, 1.0)
    quality.set_xlabel("F1-macro")
    quality.set_xticks([0.8, 0.9, 1.0], ["0,8", "0,9", "1,0"])
    quality.set_ylim(len(rows) - 0.5, -0.5)
    quality.tick_params(axis="both", length=3.5, width=0.9, color="#17212B", pad=4)
    for yi, row in zip(y, rows):
        score = float(row["s2_oof_f1_macro"])
        label_x = score + 0.009 if score < 0.85 else score - 0.009
        quality.text(label_x, yi, f'{score:.3f}'.replace(".", ","),
                     ha="left" if score < 0.85 else "right", va="center",
                     fontsize=8.8, color="#17212B")

    offsets = {"P50": -0.12, "P95": 0.0, "P99": 0.12}
    for key, column in [("P50", "http_p50_ms"), ("P95", "http_p95_ms"), ("P99", "http_p99_ms")]:
        latency.scatter([float(row[column]) for row in rows],
                        [yi + offsets[key] for yi in y],
                        s=46, marker=markers[key], color=colors[key],
                        edgecolor="#17212B", linewidth=0.65, label=key, zorder=3)
    latency.set_xscale("log")
    latency.set_xlim(0.7, 75)
    latency.set_yticks(y, labels)
    latency.tick_params(axis="y", left=False, labelleft=False)
    latency.invert_yaxis()
    latency.set_ylim(len(rows) - 0.5, -0.5)
    latency.set_xlabel("Latência HTTP (ms, escala logarítmica)")
    latency.set_xticks([1, 10, 50], ["1", "10", "50"])
    latency.tick_params(axis="x", length=3.5, width=0.9, color="#17212B", pad=4)
    latency.legend(frameon=False, ncol=3, loc="lower left",
                   bbox_to_anchor=(0.0, 1.01), fontsize=9.5,
                   handletextpad=0.35, columnspacing=0.8)

    # Keep a single strong baseline per panel; explicitly avoid chart grids.
    for ax in (quality, latency):
        ax.grid(False)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
        for side in ("left", "bottom"):
            ax.spines[side].set_color("#17212B")
            ax.spines[side].set_linewidth(1.0)
    quality.spines["left"].set_visible(False)
    quality.tick_params(axis="y", length=0, pad=5)
    fig.subplots_adjust(left=0.27, right=0.985, top=0.85, bottom=0.18, wspace=0.18)
    save(fig, "figura_2_qualidade_latencia")


if __name__ == "__main__":
    methodology()
    performance()
    print("Generated: " + ", ".join(str(path.relative_to(ROOT)) for path in sorted(OUT.glob("figura_*.png"))))
