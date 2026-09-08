# Fluxo reproduzível do estudo UAVIDS-2025

Este é o ponto de entrada do código científico novo. O DVC e a API antiga não são necessários para executar os experimentos atuais.

## Ambiente

Criar um ambiente Python 3.12 separado e instalar `requirements-research.txt`. As versões registradas correspondem à execução de 7 de setembro de 2026.

```powershell
python -m venv .venv-research
.\.venv-research\Scripts\python.exe -m pip install -r requirements-research.txt
```

O ambiente usado na rodada registrada foi `.venv`, porque já continha as versões necessárias. Uma reprodução independente deve usar um ambiente limpo.

## Ordem de execução

```powershell
# 1. Identidade dos dados, auditoria e folds candidatos
.\.venv\Scripts\python.exe src\uavids_study\data_audit.py

# 2. Notebook narrativo da auditoria
.\.venv\Scripts\python.exe tools\build_research_notebook.py

# 3. Painel preditivo completo; jobs válidos são retomados
.\.venv\Scripts\python.exe src\uavids_study\predictive_experiment.py

# 4. Relatório, tabelas, figuras e notebook de resultados
.\.venv\Scripts\python.exe tools\build_predictive_notebook.py

# 5. Testes metodológicos
.\.venv\Scripts\python.exe -m unittest discover -s tests -v

# 6. Tuning aninhado e estabilidade por sementes
.\.venv\Scripts\python.exe src\uavids_study\nested_tuning.py
.\.venv\Scripts\python.exe tools\build_tuning_notebook.py
.\.venv\Scripts\python.exe src\uavids_study\predictive_experiment.py --config configs\stability_s2_v3.json
.\.venv\Scripts\python.exe tools\build_stability_notebook.py

# 7. Congelar candidatos e medir inferência local
.\.venv\Scripts\python.exe src\uavids_study\freeze_models.py
.\.venv\Scripts\python.exe src\uavids_study\local_benchmark.py
.\.venv\Scripts\python.exe tools\build_local_benchmark_notebook.py
```

Filtros podem ser usados para smoke tests. O manifesto continuará indicando que a execução está incompleta até existirem todos os jobs planejados.

```powershell
.\.venv\Scripts\python.exe src\uavids_study\predictive_experiment.py --protocols S0 --folds 0 --models dummy_prior,logistic_regression
```

## Artefatos principais

- `protocol/scope.md`: tarefa, populações e limites.
- `protocol/evaluation_v1.md`: regras congeladas do baseline.
- `configs/predictive_baseline_v1.json`: parâmetros executáveis.
- `research_artifacts/data_audit/`: identidade, dicionário, diagnóstico e folds.
- `results/predictive_baseline_v1/job_predictions/`: predições e probabilidades OOF por job.
- `results/predictive_baseline_v1/metrics_pooled_oof.csv`: métricas recalculadas na população OOF completa.
- `reports/predictive_baseline_v1/`: tabelas, figuras e interpretação.
- `notebooks/research/`: notebooks narrativos gerados.

Os diretórios `job_predictions` e `job_records` são a fonte dos resultados agregados. Se tabelas ou figuras forem alteradas, regenerá-las desses arquivos sem retreinar.

## Estado científico

O estudo concluído até aqui contém auditoria, protocolos S0/S1/S2, ablação de `FlowID`, tuning aninhado exploratório, estabilidade de Random Forest/XGBoost e benchmark Docker local dos dois artefatos congelados. CNN, GNN, stacking, múltiplos datasets, Kubernetes e `tc-netem` estão fora desta versão.

## Benchmark Docker local v2

Decisão registrada em 8 de setembro de 2026: CNN, GNN, stacking, Kubernetes e `tc-netem` não integram esta versão. O benchmark usa os artefatos congelados de XGBoost e Random Forest, sem recalcular desempenho preditivo nos dados de ajuste.

```powershell
docker version
.\.venv\Scripts\python.exe src\uavids_study\docker_benchmark.py
```

Configuração executável: `configs/docker_local_v2.json`. Protocolo: `protocol/docker_local_v2.md`. Os registros finais são gravados em `benchmarks/docker_local_v2/` e os resumos em `reports/docker_local_v2/`. A pasta `docker_local_v1` contém um piloto descartado devido ao atraso Nagle/delayed ACK documentado no protocolo e em `protocol/deviations.md`.

O comando constrói a imagem, valida os hashes dos modelos, executa um container por modelo com 0,5 CPU e 512 MiB, mede latência HTTP, throughput e amostras de CPU/RAM, remove os containers ao final e preserva a imagem para auditoria. Os resultados descrevem Docker Desktop/WSL2 em loopback; não representam bateria, rádio, ARM ou um drone físico.

Após uma execução completa, reconstruir o notebook de análise a partir dos resultados preservados:

```powershell
.\.venv\Scripts\python.exe tools\build_docker_benchmark_notebook.py
```
