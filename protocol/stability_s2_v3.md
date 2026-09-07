# Protocolo de estabilidade por sementes em S2

Congelado em 7 de setembro de 2026 antes da execução de `stability_s2_v3`.

Esta rodada mantém fixos os atributos, folds e hiperparâmetros e varia somente a semente de ajuste (`20260907`, `20260908`, `20260909`). O objetivo é separar variação algorítmica da variação muito maior causada pela composição dos grupos de origem.

- XGBoost usa o candidato escolhido nos cinco folds internos da v2.
- Random Forest usa o candidato escolhido em quatro de cinco folds na v2.
- Protocolos: cinco folds externos S2 persistidos.
- Resultados: métricas por fold e semente, predições OOF completas para cada semente, probabilidades, tempos e tamanhos.

As três sementes não são tratadas como datasets independentes. A rodada continua exploratória porque as configurações foram selecionadas após v1/v2. GNN, MLP e CNN não participam desta análise.
