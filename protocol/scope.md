# Escopo congelado do artigo

Data da decisão final desta versão: 8 de setembro de 2026.

Este registro transforma as decisões já tomadas no plano em regras verificáveis. Ele poderá ser alterado antes do primeiro treinamento comparativo, mas toda mudança deverá entrar em `protocol/deviations.md` com data, motivo e efeito esperado. Mudanças motivadas pelo resultado do teste final não serão aceitas.

## Tarefa e unidade de inferência

- Tarefa principal: classificação multiclasse em cinco classes (`Normal Traffic`, `Blackhole Attack`, `Flooding Attack`, `Sybil Attack` e `Wormhole Attack`).
- Unidade predita: um registro de fluxo do CSV público, representado somente por atributos que o protocolo declare disponíveis no instante da decisão.
- Tarefas binária e de quatro classes: secundárias e condicionadas ao orçamento; não substituem a análise principal.
- Métrica preditiva primária: F1 macro. Métricas por classe, matriz de confusão e balanced accuracy acompanham a métrica primária.

## Populações avaliadas

- S0: novos fluxos da mesma mistura empírica, usado como referência de interpolação.
- S1: fluxos cuja assinatura numérica exata não aparece no treino, usado para medir sensibilidade a padrões repetidos.
- S2: fluxos de endereços de origem não vistos no treino. Endereço não é tratado como prova de identidade física do UAV.
- S3: novas execuções ou cenários de simulação; indisponível no CSV público porque faltam identificadores de execução confiáveis.

S0, S1 e S2 respondem a perguntas diferentes. Nenhum resultado será chamado simplesmente de “generalização” sem nomear a população correspondente.

## Atributos e contexto

- `FlowID` fica somente para rastreabilidade e para a reprodução fiel de trabalhos que comprovadamente o tenham usado. Ele será excluído da análise principal.
- `SrcAddr` e `DstAddr` são metadados de grupos/diagnóstico. Sua inclusão como preditores exigirá uma ablação explícita.
- `Protocol` será excluído enquanto permanecer constante (`UDP`).
- As 18 variáveis numéricas registradas em `data_manifest.json` formam a assinatura S1 e o painel tabular inicial.
- A disponibilidade causal e local das variáveis permanece não confirmada. Até esclarecimento, o resultado representa classificação de vetores de fluxo prontos, sem alegar um IDS embarcado completo.
- A sequência de `FlowID` não será interpretada como tempo. Modelos temporais, GNN e tempo até detecção estão fora desta versão.

## Escopo do artigo

O núcleo desta versão compara Random Forest e XGBoost sob protocolos resistentes a identificadores e mede seu custo de atendimento em Docker local. MLP e outros modelos já executados permanecem apenas como baselines exploratórios.

Outros datasets, ataques desconhecidos, aprendizado federado, votação bizantina, CNN, GNN, modelos temporais, stacking, Kubernetes e `tc-netem` estão fora desta versão. O benchmark usa Docker local em loopback, sem afirmar equivalência com hardware embarcado.

## Exposição prévia e limites

Os autores do projeto já examinaram o dataset completo e notebooks anteriores. O reinício do código não torna o UAVIDS-2025 um conjunto historicamente intocado. O protocolo, os folds persistidos e a separação entre desenvolvimento e teste reduzirão decisões adaptadas aos resultados, mas não apagam essa exposição.

Permanecem manuais e pendentes: equipamento e horas disponíveis, publicação-alvo, licença exibida na fonte canônica, origem/licença dos notebooks de terceiros e respostas dos autores sobre geração, sessões, timestamps e disponibilidade dos atributos.
