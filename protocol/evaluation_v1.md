# Protocolo de avaliação preditiva v1

Congelado em 7 de setembro de 2026, antes da execução do painel descrito abaixo.

## Status e finalidade

Esta é uma comparação exploratória de baselines com hiperparâmetros fixos. Ela valida o fluxo completo, estima dificuldade e custo e identifica problemas do protocolo. Ela não é a comparação confirmatória final e seus resultados não serão usados como teste final depois de alterar modelos ou espaços de busca.

## Dados e partições

- Artefato: UAVIDS-2025 público, identificado no `data_manifest.json`.
- Tarefa: cinco classes na ordem explícita registrada na configuração.
- Atributos principais: 18 variáveis numéricas, sem `FlowID`, `SrcAddr`, `DstAddr` e `Protocol`.
- Protocolos: cinco folds externos persistidos de S0, S1 e S2.
- Cada linha é teste exatamente uma vez por protocolo. O conjunto complementar forma o treino daquele fold.
- Nenhuma remoção de duplicata ou correção de `PacketDropRate` será feita nesta versão.

## Modelos e orçamento

O arquivo `configs/predictive_baseline_v1.json` é a fonte executável dos parâmetros. A rodada usa uma semente (`20260907`) e quatro threads, registrando tempo de ajuste, tempo de inferência, avisos, número de iterações quando disponível e tamanho serializado.

O painel contém Dummy por prior, regressão logística, Random Forest, Extra Trees, XGBoost e MLP compacta. Regressão e MLP recebem `StandardScaler` ajustado exclusivamente no treino de cada fold. Os demais recebem os valores originais. Não há tuning nesta rodada.

A MLP usa um limite fixo de 100 épocas e não usa early stopping, pois a API do scikit-learn não permite passar diretamente uma validação interna com os grupos S1/S2. Uma rodada futura poderá implementar early stopping manual por grupo.

`random_forest_with_flow_id` é uma ablação diagnóstica separada, motivada pela aparente inconsistência de R7 sobre a remoção de identificadores. Ela não concorre como modelo principal e seus resultados não orientarão a escolha de atributos.

## Métricas e artefatos

- Primária: F1 macro com as cinco classes sempre presentes na ordem congelada e `zero_division=0`.
- Secundárias: accuracy, balanced accuracy, precision/recall/F1 por classe, log loss, taxa de falso alarme e taxa de ataques perdidos.
- Custo: segundos de ajuste, segundos de inferência do lote do fold, microssegundos amortizados por registro e tamanho serializado.
- Persistência: probabilidades e predições por linha/fold, métricas por fold, matriz de confusão e manifesto da execução.

As métricas são recalculadas a partir das predições salvas. Uma diferença S0–S1 será descrita como sensibilidade ao protocolo e à população; ela não será chamada automaticamente de vazamento.

## Regras de falha e decisão

- Uma falha gera um registro de erro; não vira métrica zero e não é removida silenciosamente.
- Avisos de convergência permanecem no registro e impedem afirmar que o modelo foi plenamente otimizado.
- O melhor modelo não será escolhido somente pelo maior F1. A etapa seguinte examinará qualidade, estabilidade, custo e comportamento por classe.
- A CNN residual de R4 não integra v1 porque o ambiente não contém PyTorch/TensorFlow e os detalhes de reprodução ainda precisam ser confirmados. Não será usada uma substituição arbitrária chamada de reprodução.
- GNN, janelas temporais e tempo até detecção foram retirados a pedido do pesquisador e pela ausência de metadados confiáveis.
