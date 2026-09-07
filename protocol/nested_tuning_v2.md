# Protocolo exploratório de tuning aninhado v2

Congelado em 7 de setembro de 2026 antes da execução de `nested_tuning_v2`.

## Motivo e status

O baseline v1 apontou XGBoost e Random Forest como os candidatos mais fortes entre qualidade e custo. Como essa escolha consultou resultados dos mesmos folds, a v2 continua exploratória e não cria um novo teste confirmatório. Seu objetivo é avaliar o procedimento de seleção interna e preparar a escolha de artefatos para o benchmark de sistemas.

## Avaliação externa

- Protocolo: S2, cinco folds externos já persistidos.
- População: endereços de origem não vistos no treino do fold.
- Atributos: os mesmos 18 atributos principais, sem identidade.
- Métrica externa primária: F1 macro OOF com as cinco classes fixas.
- Cada teste externo é acessado somente depois de selecionar um candidato nos dados internos do treino externo.

## Seleção interna

- Três folds `StratifiedGroupKFold` construídos somente no treino externo.
- Grupo: `s2_group`/endereço de origem; nenhum grupo pode cruzar treino e validação internos.
- Métrica: média do F1 macro nos três folds internos.
- Três candidatos fixos para cada família, definidos em `configs/nested_tuning_v2.json`.
- Empate: candidatos até 0,0001 do maior valor usam menor `complexity_rank`; persistindo o empate, menor `candidate_id` lexicográfico.
- O modelo escolhido é reajustado em todo o treino externo e avaliado uma vez no teste externo.

Cada job registra os nove fits internos, o fit externo final, duração, avisos, hiperparâmetros selecionados, predições e probabilidades externas.

## Limites

O espaço é deliberadamente pequeno e não garante o ótimo de nenhuma família. Há uma única semente. A comparação de tempo permanece diagnóstica. MLP e CNN não entram nesta rodada: a MLP requer validação interna por grupo para early stopping, e a CNN de R4 ainda não possui ambiente/detalhes de reprodução confirmados. GNN permanece suspensa.

Uma eventual escolha para implantação deverá considerar resultado interno, estabilidade externa, tamanho, latência e múltiplas sementes. A seleção não será feita apenas pelo melhor fold externo.
