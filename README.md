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

O CSV vem do [depósito dos autores no Zenodo](https://zenodo.org/records/15336998). O script verifica tamanho e SHA-256 e recusa substituir um arquivo existente divergente. Fonte, DOI e checksum estão em `provenance/data_source.json`. O caminho `notebooks/data/raw/` foi mantido para preservar a compatibilidade.

## Roteiro científico

- [Plano revisado](PLANO_CIENTIFICO_UAVIDS2025.md): perguntas, evidências existentes, experimentos faltantes e critérios de interpretação.
- [Fluxo de execução](RESEARCH_WORKFLOW.md): comandos de auditoria, treino, agregação e análise.
- [Escopo vigente](protocol/scope.md): populações avaliadas e limites das conclusões.
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

Prioridades: conferir resultados salvos, avaliar derivadas por ablação e quantificar incerteza. Trocar seeds ou recomeçar código não cria teste historicamente intocado.

## MLflow opcional

MLflow serve para consultar e comparar experimentos. CSV/JSON e predições salvas continuam sendo a fonte científica. O exportador usa [registro manual de tracking](https://mlflow.org/docs/latest/ml/tracking/tracking-api/), sem registry, promoção de modelo ou treino automático.

```powershell
uv pip install --python .venv-research/Scripts/python.exe -r requirements-tracking.txt
.\.venv-research\Scripts\python.exe tools\export_mlflow.py --config configs\predictive_baseline_v1.json
.\.venv-research\Scripts\mlflow.exe ui --backend-store-uri sqlite:///tracking/mlflow.db --port 5002
```

O exportador confere configuração e checksums e evita duplicar jobs. `--dry-run` valida sem instalar MLflow; `--include-predictions` inclui os CSVs comprimidos. Tracking local fica fora do Git.

## Custo e disponibilidade

Inferência em processo pode acompanhar a análise. Docker permanece complementar: caracteriza HTTP/loopback na máquina medida, sem representar ARM, rádio, voo ou energia. Seu protocolo e resultados foram preservados; não há Compose de produção no núcleo.

Arquivos grandes ficam fora do Git. Para submissão, preparar depósito de configurações, partições, predições e checksums conforme as licenças. Em clone sem resultados, executar as rodadas antes de verificar seus artefatos.

Repositório: [Messyas/desafio-UAV](https://github.com/Messyas/desafio-UAV).
