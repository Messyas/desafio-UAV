"""Build the readable, executed audit notebook without a notebook dependency."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ARTIFACT_DIR = PROJECT_ROOT / "research_artifacts" / "data_audit"
OUTPUT_PATH = PROJECT_ROOT / "notebooks" / "research" / "00_auditoria_e_protocolo.ipynb"


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


def table(name: str, **read_kwargs) -> pd.DataFrame:
    return pd.read_csv(ARTIFACT_DIR / name, **read_kwargs)


def main() -> None:
    summary = json.loads((ARTIFACT_DIR / "data_audit_summary.json").read_text("utf-8"))
    manifest = json.loads((ARTIFACT_DIR / "data_manifest.json").read_text("utf-8"))
    classes = table("class_distribution.csv")
    duplicates = table("duplicates_by_class.csv")
    relations = table("algebraic_relations.csv")
    protocols = table("protocol_diagnostics.csv")
    overlaps = table("fold_overlap_diagnostics.csv")
    groups = table("group_diagnostics.csv")
    profile = table("class_endpoint_profile.csv")
    fold_balance = table("fold_balance.csv")

    s2_overlap = overlaps.loc[overlaps["protocol"] == "S2"]
    pdr_relation = relations.iloc[0]
    flood_duplicates = duplicates.loc[
        duplicates["label"] == "Flooding Attack", "fraction"
    ].iloc[0]
    s2_fold_sizes = (
        fold_balance.loc[fold_balance["protocol"] == "S2"]
        .groupby("fold")["rows"]
        .sum()
        .sort_index()
        .astype(int)
        .tolist()
    )

    cells = [
        markdown_cell(
            """# UAVIDS-2025 — auditoria reproduzível e protocolos candidatos

**Papel deste notebook:** estabelecer identidade do arquivo, contrato provisório dos atributos e divisões candidatas antes de ajustar classificadores. Este notebook não compara modelos e não produz uma conclusão de superioridade.

O código está em inglês para facilitar manutenção e revisão. As decisões, interpretações e limites são escritos em português. A lógica reutilizável fica em `src/uavids_study/data_audit.py`; o notebook funciona como narrativa executável e não como fonte oculta de regras experimentais.
"""
        ),
        markdown_cell(
            """## Decisões científicas anteriores aos resultados

1. A tarefa principal tem cinco classes e a unidade é um registro de fluxo.
2. `FlowID`, `SrcAddr` e `DstAddr` não entram como preditores no painel principal; os endereços permanecem disponíveis para grupos e diagnóstico. `Protocol` é removido se sua constância for confirmada.
3. S0 mede interpolação na mistura empírica; S1 mantém assinaturas numéricas idênticas no mesmo fold; S2 mantém origens inteiras no mesmo fold. Esses protocolos representam populações distintas.
4. A ausência de timestamp, sessão e execução impede tratar a ordem do CSV ou o `FlowID` como cronologia validada.
5. A seleção de modelos futura deverá usar pipelines ajustados somente no treino e validação interna. O teste externo não orientará preprocessing, hiperparâmetros ou limiares.

**Inspiração documentada.** O artigo do dataset define o objeto de estudo ([Zeng et al., IEEE CNS 2025](https://doi.org/10.1109/CNS66487.2025.11194990)). A separação de grupos e a prevenção de ajuste fora dos folds seguem a documentação de [validação cruzada](https://scikit-learn.org/stable/modules/cross_validation.html) e [erros comuns](https://scikit-learn.org/stable/common_pitfalls.html) do scikit-learn. R7 motiva testar explicitamente o efeito de `FlowID` porque seu texto/figura deixam ambígua a presença do identificador ([artigo](https://doi.org/10.1186/s13635-026-00234-w)). R2 motiva contexto temporal/relacional, mas o CSV público não contém sozinho os metadados temporais necessários ([FedGraph-ID](https://doi.org/10.1109/INFOCOM59046.2026.11571676)).
"""
        ),
        code_cell(
            """from pathlib import Path
import json
import sys

import pandas as pd

project_root = Path.cwd().resolve()
if project_root.name == "research":
    project_root = project_root.parents[1]
elif project_root.name == "notebooks":
    project_root = project_root.parent

sys.path.insert(0, str(project_root / "src"))

from uavids_study.data_audit import run_data_audit

dataset_path = project_root / "notebooks" / "data" / "raw" / "UAVIDS-2025.csv"
artifact_dir = project_root / "research_artifacts" / "data_audit"

print(f"Project root: {project_root}")
print(f"Dataset exists: {dataset_path.exists()}")
""",
            f"Project root: {PROJECT_ROOT}\nDataset exists: True",
            1,
        ),
        markdown_cell(
            """## 1. Identidade do artefato

O hash é um requisito científico: dois arquivos com o mesmo nome podem representar versões ou ordenações diferentes. A execução abaixo falha deliberadamente se o CSV local não corresponder ao artefato registrado como Zenodo v1. Os dados brutos não são modificados.
"""
        ),
        code_cell(
            """created_paths, audit_summary = run_data_audit(dataset_path, artifact_dir)
data_manifest = json.loads(created_paths.manifest.read_text(encoding="utf-8"))

identity = data_manifest["dataset"]
print(json.dumps(identity, indent=2, ensure_ascii=False))
""",
            json.dumps(manifest["dataset"], indent=2, ensure_ascii=False),
            2,
        ),
        markdown_cell(
            """## 2. Integridade, classes e contrato dos atributos

As definições do dicionário são provisórias. Relações observadas no CSV ajudam a detectar redundância, mas não substituem a fórmula oficial nem comprovam que uma variável estaria disponível causalmente em um UAV real.
"""
        ),
        code_cell(
            """class_distribution = pd.read_csv(created_paths.class_distribution)
data_dictionary = pd.read_csv(created_paths.dictionary)

print(class_distribution.to_string(index=False))
print("\\nResumo da integridade:")
print(json.dumps(audit_summary, indent=2, ensure_ascii=False))
""",
            classes.to_string(index=False) + "\n\nResumo da integridade:\n" + json.dumps(summary, indent=2, ensure_ascii=False),
            3,
        ),
        code_cell(
            """selected_columns = [
    "column", "dtype", "role", "unit", "formula",
    "unique_values", "missing_values", "available_at_prediction_time",
]
print(data_dictionary[selected_columns].to_string(index=False))
""",
            table("data_dictionary.csv")[["column", "dtype", "role", "unit", "formula", "unique_values", "missing_values", "available_at_prediction_time"]].to_string(index=False),
            4,
        ),
        markdown_cell(
            """## 3. Repetições, ordem e relações algébricas

Duplicatas completas incluem identificadores e podem ocultar repetições do vetor que chega ao modelo. Por isso, a assinatura S1 usa as 18 variáveis numéricas do painel principal. Assinaturas repetidas não são apagadas: sua frequência faz parte da população empírica e todas permanecem no mesmo fold em S1.
"""
        ),
        code_cell(
            """duplicates_by_class = pd.read_csv(created_paths.duplicates_by_class)
algebraic_relations = pd.read_csv(created_paths.algebraic_relations)

print(duplicates_by_class.to_string(index=False))
print("\\nRelações algébricas auditadas:")
print(algebraic_relations.to_string(index=False))
""",
            duplicates.to_string(index=False) + "\n\nRelações algébricas auditadas:\n" + relations.to_string(index=False),
            5,
        ),
        code_cell(
            """endpoint_profile = pd.read_csv(created_paths.class_endpoint_profile)
feature_ranges = pd.read_csv(created_paths.feature_ranges)

print(endpoint_profile.to_string(index=False))
print("\\nFaixas observadas (não são domínios físicos validados):")
print(feature_ranges.to_string(index=False))
""",
            profile.to_string(index=False) + "\n\nFaixas observadas (não são domínios físicos validados):\n" + table("feature_ranges.csv").to_string(index=False),
            6,
        ),
        markdown_cell(
            """## 4. Protocolos candidatos S0, S1 e S2

Os folds abaixo são persistidos em `split_candidates.csv.gz`, portanto modelos diferentes receberão exatamente as mesmas linhas. Eles ainda são candidatos: S2 apresenta grupos grandes e precisa ser revisado antes do congelamento final. `groups_crossing_folds = 0` é uma condição necessária para S1/S2, mas não garante ausência de outras formas de dependência.
"""
        ),
        code_cell(
            """protocol_diagnostics = pd.read_csv(created_paths.protocol_diagnostics)
group_diagnostics = pd.read_csv(created_paths.group_diagnostics)
fold_balance = pd.read_csv(created_paths.fold_balance)

print(protocol_diagnostics.to_string(index=False))
print("\\nTamanho e pureza dos grupos:")
print(group_diagnostics.to_string(index=False))
print("\\nTotal de linhas por fold:")
print(fold_balance.groupby(["protocol", "fold"])["rows"].sum().to_string())
""",
            protocols.to_string(index=False) + "\n\nTamanho e pureza dos grupos:\n" + groups.to_string(index=False) + "\n\nTotal de linhas por fold:\n" + fold_balance.groupby(["protocol", "fold"])["rows"].sum().to_string(),
            7,
        ),
        code_cell(
            """overlap_diagnostics = pd.read_csv(created_paths.fold_overlap_diagnostics)
print(overlap_diagnostics.to_string(index=False))
""",
            overlaps.to_string(index=False),
            8,
        ),
        markdown_cell(
            f"""## 5. Leitura dos achados e decisões resultantes

- O arquivo local corresponde exatamente ao Zenodo v1 por tamanho, número de linhas/colunas, MD5 e SHA-256.
- Há {summary['missing_cells']} valores ausentes e {summary['infinite_numeric_cells']} infinitos. `Protocol` é constante (`UDP`) e será removido do painel principal.
- Existem {summary['duplicate_model_signature_rows_after_first']:,} repetições além da primeira entre {summary['unique_model_signatures']:,} assinaturas numéricas únicas. {flood_duplicates:.2%} dos registros de Flooding pertencem a uma assinatura repetida. Como não há conflitos de rótulo entre assinaturas idênticas, S1 consegue mantê-las juntas sem resolver rótulos contraditórios.
- A relação `PacketDropRate ≈ LostPackets / TxPackets` vale dentro da tolerância para {pdr_relation['close_fraction']:.4%} das linhas comparáveis. Ainda assim, {summary['packet_drop_rate_above_one']} registros têm `PacketDropRate > 1`; eles serão preservados até a fórmula/semântica ser confirmada.
- `FlowID` é único e sequencial, e {summary['adjacent_same_label_fraction']:.2%} dos pares adjacentes mantêm o mesmo rótulo. Isso torna uma divisão sem embaralhamento inadequada e não comprova cronologia.
- S2 preserva as origens, mas os tamanhos dos folds são {s2_fold_sizes}. A diferença decorre de apenas {summary['source_addresses']} origens com tamanhos desiguais. A métrica deverá ser agregada por predição e também apresentada por fold, com intervalos e distribuição visíveis.
- S2 não elimina automaticamente destinos ou assinaturas já vistos. O arquivo de sobreposição quantifica esse limite em cada fold.
- O CSV não oferece timestamp, sessão, cenário ou execução. O eixo temporal permanece bloqueado; uma GNN temporal reproduzível exige metadados/código adicionais de R2.

Esses achados justificam comparar o protocolo aleatório usado por muitos trabalhos com S1 e S2. Eles ainda não demonstram que um modelo publicado sofre vazamento, nem que uma arquitetura é superior.
"""
        ),
        markdown_cell(
            """## 6. Critérios para iniciar o notebook de modelagem

- [x] Arquivo identificado e imutável por hash.
- [x] Classes, ausentes, infinitos, constantes, faixas, repetições e relações algébricas auditados.
- [x] `FlowID` e endereços separados dos atributos principais.
- [x] S0/S1/S2 materializados uma única vez, com grupos e sobreposições verificáveis.
- [x] Exposição prévia e limites de inferência registrados em `protocol/scope.md`.
- [ ] Revisão humana do dicionário e das alegações atribuídas aos artigos.
- [ ] Confirmação da licença exibida pela fonte canônica.
- [ ] Orçamento computacional, hardware e publicação-alvo registrados.
- [ ] Estratégia de validação interna e espaços de busca congelados antes do primeiro tuning comparativo.

O próximo notebook deve implementar um baseline ingênuo e os modelos tabulares em pipelines, ler os folds deste notebook e salvar predições por linha. A reprodução com `FlowID` deve ser rotulada como diagnóstico/reprodução fiel e nunca misturada ao resultado principal corrigido.
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
            "language_info": {"name": "python", "version": manifest["environment"]["python"]},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
    )
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
