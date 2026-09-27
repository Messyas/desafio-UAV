# Fluxo científico reproduzível

O método está em protocol/ e o ciclo revisado em PLANO_CIENTIFICO_UAVIDS2025.md. A nova ablação está implementada com orçamento próprio; as rodadas anteriores permanecem históricas. O protocolo detalhado está em protocol/feature_ablation_v4.md.

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

## Novo ciclo: ablação pareada

Verificar dados e manter os folds já auditados. Não executar `data_audit.py` novamente sobre uma pasta usada em rodadas concluídas para substituir partições.

```powershell
.\.venv-research\Scripts\python.exe tools\audit_derived_features.py
.\.venv-research\Scripts\python.exe src\uavids_study\feature_ablation.py --dry-run --protocols S2
.\.venv-research\Scripts\python.exe src\uavids_study\feature_ablation.py --protocols S2
.\.venv-research\Scripts\python.exe src\uavids_study\paired_analysis.py --protocols S2
.\.venv-research\Scripts\python.exe tools\build_ablation_report.py
```

S2 tem 50 jobs. Os filtros não mudam a configuração congelada: esse estágio não completa o painel de 150 jobs. Para completar S0/S1 e reconstruir a análise de todos os protocolos:

```powershell
.\.venv-research\Scripts\python.exe src\uavids_study\feature_ablation.py --protocols S0,S1
.\.venv-research\Scripts\python.exe src\uavids_study\paired_analysis.py
.\.venv-research\Scripts\python.exe tools\build_ablation_report.py
.\.venv-research\Scripts\python.exe tools\verify_control_parity.py
```

Retomada verifica dataset, splits, parâmetros, código e ambiente antes de reutilizar predições. Mudanças exigem outro experiment_id. O controle A0 é retreinado neste contrato; resultados antigos não são combinados. Executar `--dry-run` permite conferir orçamento sem ajustar modelos.

Para conservar também o traceback de invocações que falharem, substituir `src\uavids_study\feature_ablation.py` por `tools\run_ablation.py` nos comandos de execução; os argumentos e o executor são os mesmos. Diagnósticos ficam em research_artifacts/failures/.

Métricas por fold ficam em results/feature_ablation_v4/. Análise pareada, métricas OOF, classes, confusões e figuras ficam em reports/feature_ablation_v4/. A análise exige todos os folds/condições de cada protocolo solicitado; os intervalos são condicionais a predições fixas, por grupos, não à incerteza completa de retreinamento.

### Repetição completa por sementes

```powershell
.\.venv-research\Scripts\python.exe src\uavids_study\feature_ablation.py --config configs\feature_ablation_stability_v5.json --dry-run
.\.venv-research\Scripts\python.exe src\uavids_study\feature_ablation.py --config configs\feature_ablation_stability_v5.json
.\.venv-research\Scripts\python.exe src\uavids_study\paired_analysis.py --config configs\feature_ablation_stability_v5.json
.\.venv-research\Scripts\python.exe tools\build_ablation_report.py --config configs\feature_ablation_stability_v5.json
```

São 150 jobs próprios em S2: todas as condições, ambos os modelos, cinco folds, três seeds. Não repetir apenas o braço que ganhou; reportar seeds separadamente, sem teste t que as trate como populações independentes.

### Sensibilidade secundária de PacketDropRate

```powershell
.\.venv-research\Scripts\python.exe src\uavids_study\feature_ablation.py --config configs\pdr_sensitivity_v6.json
.\.venv-research\Scripts\python.exe src\uavids_study\sensitivity_analysis.py
.\.venv-research\Scripts\python.exe tools\package_research.py --config configs\pdr_sensitivity_v6.json
```

São 10 jobs novos, com A0 e recorte [0,1], comparados ao A0 original completo de S2 v4. Não chamar o recorte de correção de defeito não demonstrado. Não usar `build_ablation_report.py` nesta análise de um único braço; sua tabela é clipping_comparisons.csv.
O pacote dessa sensibilidade inclui também os dez controles A0 S2 v4 necessários à comparação pareada, com hashes verificados.

### Depósito local e reprodução

```powershell
.\.venv-research\Scripts\python.exe tools\package_research.py
```

Gera ZIP local em research_artifacts/releases/, com manifesto SHA-256 e escopo explícito dos protocolos efetivamente completos. Inclui código, configurações, folds, predições e relatórios; o CSV bruto é obtido da fonte canônica, sem redistribuição neste ZIP. Revisão de licenças e publicação permanecem etapas humanas posteriores.

Para repetir em outra máquina/ambiente, criar cópia da configuração com novo experiment_id e registrar a reprodução; não tentar anexar treinamentos de ambiente diferente ao manifesto original. O pacote preserva os hashes e o ambiente da execução original. Reproduzir o pipeline completo em clone limpo antes de submissão.

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

Esse comando mede os candidatos históricos e seus parâmetros próprios; não representa automaticamente as novas condições A0–A4. Para relacionar ablação e custo, preparar protocolo/artefatos dos pipelines exatos antes de comparar. Critérios para a redação estão em protocol/article_readiness.md.

Docker, opcional e fora do requisito mínimo:

```powershell
.\.venv-research\Scripts\python.exe src\uavids_study\docker_benchmark.py
.\.venv-research\Scripts\python.exe tools\build_docker_benchmark_notebook.py
```

Exige Docker disponível e executa nova medição de bancada com configs/docker_local_v2.json. Não faz parte da preparação dos dados, treino ou tracking. Descreve Docker Desktop/WSL2 em loopback; não mede bateria ou hardware embarcado.
