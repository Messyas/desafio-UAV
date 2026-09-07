# Congelamento dos candidatos para benchmark

Data: 7 de setembro de 2026.

XGBoost e Random Forest foram congelados para medir custo de inferência local e em container. A configuração executável está em `configs/deployment_candidates_v1.json`.

- XGBoost: candidato base, escolhido internamente nos cinco folds da v2.
- Random Forest: 240 árvores, `max_features=sqrt` e `min_samples_leaf=2`, escolhido em quatro de cinco folds da v2.
- Ajuste do artefato: todos os 122.171 registros, somente após encerrar as análises preditivas v1–v3.
- Finalidade: benchmark de sistemas. Métricas calculadas nos mesmos dados usados no ajuste seriam inválidas e não serão produzidas.
- Entrada: vetor `float64` de 18 atributos na ordem congelada.
- Saída: cinco probabilidades na ordem de classes congelada.

O primeiro benchmark medirá inferência em processo, sem rede. A etapa em Docker deverá usar esses mesmos hashes de modelo. Tempos de lote e de chamada individual serão reportados separadamente. Docker Desktop/WSL2 será descrito como virtualização Linux no Windows, sem equivalência com hardware embarcado.

Arquivos pickle só devem ser carregados de origem confiável e com versões compatíveis. Eles são artefatos de pesquisa locais, não formato definitivo de implantação.
