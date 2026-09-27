# UAVIDS-2025 — estudo experimental de detecção de intrusões

Este repositório investiga identificadores, protocolos de avaliação e engenharia de atributos na classificação das cinco classes do UAVIDS-2025. O objetivo é produzir evidências reproduzíveis sobre modelos tabulares, seus erros e seus limites de generalização.

Os resultados existentes são **exploratórios**. Não estabelecem superioridade sobre GNNs, economia de bateria, detecção de ataques desconhecidos ou implantação em drones. O manuscrito `ARTIGO_UAVIDS2025.docx` é histórico e precisa ser reescrito depois da revisão experimental.

## Começar

Python 3.12. DVC, Docker, FastAPI e MLflow não são necessários para o núcleo.

```powershell
uv venv --python 3.12 .venv-research
uv pip install --python .venv-research/Scripts/python.exe -r requirements.txt
.\.venv-research\Scripts\python.exe tools\fetch_dataset.py
```

Sem uv, usar `py -3.12 -m venv .venv-research` e instalar com `python.exe -m pip install -r requirements.txt` no ambiente criado. O .venv antigo contém caminhos específicos de outra instalação; não deve ser copiado como ambiente reproduzível.

O CSV vem do [depósito dos autores no Zenodo](https://zenodo.org/records/15336998). O script verifica tamanho e SHA-256 e recusa substituir um arquivo existente divergente. Fonte, DOI, checksum e licença CC BY 4.0 confirmada pela [API do registro](https://zenodo.org/api/records/15336998) estão em `provenance/data_source.json`. O caminho `notebooks/data/raw/` foi mantido para preservar a compatibilidade.

## Roteiro científico

- [Plano revisado](PLANO_CIENTIFICO_UAVIDS2025.md): perguntas, evidências existentes, experimentos faltantes e critérios de interpretação.
- [Fluxo de execução](RESEARCH_WORKFLOW.md): comandos de auditoria, treino, agregação e análise.
- [Escopo vigente](protocol/scope.md): populações avaliadas e limites das conclusões.
- [Ablação revisada](protocol/feature_ablation_v4.md): condições A0–A4, parâmetros fixos, bootstrap por grupos e sensibilidade secundária.
- [Leitura crítica dos resultados](protocol/evidence_review.md): achados, limitações e critérios para o novo artigo.
- [Plano de fechamento do artigo](PLANO_FECHAMENTO_ARTIGO.md): sequência, entregáveis e decisões antes da redação/submissão.
- [Matriz de literatura](protocol/literature_matrix.csv), [auditoria semântica](protocol/feature_semantics_audit.csv), [validade externa](protocol/external_data_feasibility.md), [inferência](protocol/statistical_review.md) e [triagem de revista](protocol/journal_screen.md): evidências e limites para a tese.
- [Minuta de manuscrito](MANUSCRIPT_DRAFT.md): texto-base conservador, pendente de reprodução e revisão científica.
- `src/uavids_study/`: implementação; `configs/`: parâmetros; `protocol/`: métodos e desvios.
- `notebooks/research/`: análise narrativa; `tests/`: invariantes metodológicas e integridade.
- `results/`: predições/registros; `reports/`: tabelas/figuras; `research_artifacts/`: auditoria/partições.
- `archive/`: material histórico e referências de terceiros, fora do fluxo ativo.

## Estado observado

Existem auditoria, 105 jobs de baseline S0/S1/S2, 10 jobs de tuning aninhado e 30 jobs de estabilidade. Conferir seus artefatos antes de aproveitar números no artigo. A reorganização não exige repetir treinamentos.

| Protocolo | População | Limite |
|---|---|---|
| S0 | Divisão estratificada aleatória | Referência de interpolação |
| S1 | Assinaturas numéricas exatas inéditas | Não equivale a sessões independentes |
| S2 | Endereços de origem inéditos | Não comprova novos UAVs físicos |
| S3 | Novas execuções/cenários | Indisponível sem metadados adicionais |

O novo ciclo foi executado: v4 concluiu 150/150 jobs A0–A4 em S0/S1/S2; v5 concluiu 150/150 em três seeds S2; v6 concluiu 10/10 para a sensibilidade ao recorte de PacketDropRate. Manifestos e relatórios são a fonte dessas contagens. As derivadas não mostraram ganho geral relevante; a interpretação crítica está em protocol/evidence_review.md. Trocar seeds ou recomeçar código não cria teste historicamente intocado.

```powershell
.\.venv-research\Scripts\python.exe src\uavids_study\feature_ablation.py --protocols S2
.\.venv-research\Scripts\python.exe src\uavids_study\paired_analysis.py --protocols S2
.\.venv-research\Scripts\python.exe tools\build_ablation_report.py
```

O executor congela dados, folds, configuração, código e ambiente; a análise recusa OOF incompleto. As derivadas ficam no pipeline e a imputação usa somente o treino. A auditoria encontrou loss_ratio praticamente redundante com PacketDropRate; seu eventual efeito precisa ser medido, sem ser anunciado como novidade.

## MLflow opcional

MLflow serve para consultar e comparar experimentos. CSV/JSON e predições salvas continuam sendo a fonte científica. O exportador usa [registro manual de tracking](https://mlflow.org/docs/latest/ml/tracking/tracking-api/), sem registry, promoção de modelo ou treino automático.

```powershell
uv pip install --python .venv-research/Scripts/python.exe -r requirements-tracking.txt
.\.venv-research\Scripts\python.exe tools\export_mlflow.py --config configs\predictive_baseline_v1.json
.\.venv-research\Scripts\python.exe tools\export_mlflow.py --config configs\feature_ablation_v4.json
.\.venv-research\Scripts\mlflow.exe ui --backend-store-uri sqlite:///tracking/mlflow.db --port 5002
```

O exportador confere configuração e checksums e evita duplicar jobs. `--dry-run` valida sem instalar MLflow; `--include-predictions` inclui os CSVs comprimidos. Tracking local fica fora do Git.

## Custo e disponibilidade

Inferência em processo pode acompanhar a análise. Docker permanece complementar: caracteriza HTTP/loopback na máquina medida, sem representar ARM, rádio, voo ou energia. Seu protocolo e resultados foram preservados; não há Compose de produção no núcleo.

Arquivos grandes ficam fora do Git. Para submissão, preparar depósito de configurações, partições, predições e checksums conforme as licenças. Em clone sem resultados, executar as rodadas antes de verificar seus artefatos.

Repositório: [Messyas/desafio-UAV](https://github.com/Messyas/desafio-UAV).
