# Fluxo científico reproduzível

O método está em protocol/ e o próximo ciclo em PLANO_CIENTIFICO_UAVIDS2025.md. Os comandos abaixo reproduzem rodadas exploratórias existentes; a nova ablação ainda precisa de implementação e configuração próprias.

## Ambiente e dados

```powershell
uv venv --python 3.12 .venv-research
uv pip install --python .venv-research/Scripts/python.exe -r requirements-research.txt
.\.venv-research\Scripts\python.exe tools\fetch_dataset.py
.\.venv-research\Scripts\python.exe tools\fetch_dataset.py --verify-only
```

A validação desta reorganização usa Python 3.12.14; as rodadas anteriores registram Python 3.12.10. Essa diferença deve permanecer explícita. Não copiar ambientes virtuais entre computadores.

## Auditoria e partições

```powershell
.\.venv-research\Scripts\python.exe src\uavids_study\data_audit.py
.\.venv-research\Scripts\python.exe tools\build_research_notebook.py
```

Saídas em research_artifacts/data_audit/. Os folds existentes foram usados nas rodadas, mas mantêm o nome histórico split_candidates.csv.gz. Isso não indica uma partição confirmatória nova. Antes de regenerar, preservar o artefato usado e conferir seu checksum; não substituir folds de uma rodada concluída.

## Rodadas preditivas históricas

```powershell
.\.venv-research\Scripts\python.exe src\uavids_study\predictive_experiment.py
.\.venv-research\Scripts\python.exe src\uavids_study\nested_tuning.py
.\.venv-research\Scripts\python.exe src\uavids_study\predictive_experiment.py --config configs\stability_s2_v3.json
```

A retomada verifica identidade dos dados e das partições antes de reaproveitar jobs. Alteração de dados ou método recebe novo experiment_id e desvio registrado; não reaproveitar uma pasta para outro experimento.

Verificação rápida de um subconjunto, sem apresentar como painel completo:

```powershell
.\.venv-research\Scripts\python.exe src\uavids_study\predictive_experiment.py --protocols S0 --folds 0 --models dummy_prior,logistic_regression
```

## Reconstruir métricas sem treinar

```powershell
.\.venv-research\Scripts\python.exe tools\rebuild_metrics.py --config configs\stability_s2_v3.json
.\.venv-research\Scripts\python.exe tools\build_predictive_notebook.py
.\.venv-research\Scripts\python.exe tools\build_tuning_notebook.py
.\.venv-research\Scripts\python.exe tools\build_stability_notebook.py
```

rebuild_metrics.py verifica os checksums antes de agregar. Atualiza tabelas e manifesto derivado, sem ajustar modelos ou substituir predições. Média de F1 por fold e F1 OOF concatenado são medidas distintas. A normalização de confusão usa denominador separado por protocolo/modelo/semente.

## Testes

```powershell
.\.venv-research\Scripts\python.exe -m unittest discover -s tests -v
```

Testes unitários usam dados sintéticos; testes de artefatos verificam as rodadas salvas. Em clone sem resultados, esses testes indicam ausência por skip; isso não equivale a aprovação científica. Conferir quais testes foram efetivamente executados.

## Tracking opcional

```powershell
.\.venv-research\Scripts\python.exe tools\export_mlflow.py --config configs\predictive_baseline_v1.json --dry-run
uv pip install --python .venv-research/Scripts/python.exe -r requirements-tracking.txt
.\.venv-research\Scripts\python.exe tools\export_mlflow.py --config configs\predictive_baseline_v1.json
.\.venv-research\Scripts\mlflow.exe ui --backend-store-uri sqlite:///tracking/mlflow.db --port 5002
```

Sem MLflow, todas as etapas continuam disponíveis. Tracking não autoriza adaptar o método a um teste declarado intocado.

## Benchmark complementar

```powershell
.\.venv-research\Scripts\python.exe src\uavids_study\freeze_models.py
.\.venv-research\Scripts\python.exe src\uavids_study\local_benchmark.py
.\.venv-research\Scripts\python.exe tools\build_local_benchmark_notebook.py
```

Artefatos ajustados em todos os dados servem somente à medição de custo, nunca à avaliação preditiva nesses dados. Protocolos: deployment_candidates_v1.md e local_benchmark_v1.md.

Docker, opcional e fora do requisito mínimo:

```powershell
.\.venv-research\Scripts\python.exe src\uavids_study\docker_benchmark.py
.\.venv-research\Scripts\python.exe tools\build_docker_benchmark_notebook.py
```

Exige Docker disponível e executa nova medição de bancada com configs/docker_local_v2.json. Não faz parte da preparação dos dados, treino ou tracking. Descreve Docker Desktop/WSL2 em loopback; não mede bateria ou hardware embarcado.
