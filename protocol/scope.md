# Escopo congelado para a primeira etapa

Data da decisão: 7 de setembro de 2026.

Este registro transforma as decisões já tomadas no plano em regras verificáveis. Ele poderá ser alterado antes do primeiro treinamento comparativo, mas toda mudança deverá entrar em `protocol/deviations.md` com data, motivo e efeito esperado. Mudanças motivadas pelo resultado do teste final não serão aceitas.

## Tarefa e unidade de inferência

- Tarefa principal: classificação multiclasse em cinco classes (`Normal Traffic`, `Blackhole Attack`, `Flooding Attack`, `Sybil Attack` e `Wormhole Attack`).
- Unidade predita: um registro de fluxo do CSV público, representado somente por atributos que o protocolo declare disponíveis no instante da decisão.
- Tarefas binária e de quatro classes: secundárias e condicionadas ao orçamento; não substituem a análise principal.
- Métrica primária futura: F1 macro. Métricas por classe, matriz de confusão, balanced accuracy e incerteza deverão acompanhar a métrica primária.

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
- A sequência de `FlowID` não será interpretada como tempo. Modelos temporais e tempo até detecção ficam bloqueados até existirem timestamp, sessão e execução confiáveis.
- Por decisão do pesquisador em 7 de setembro de 2026, GNN e contexto temporal foram suspensos nesta etapa. Agregados relacionais tabulares poderão ser reconsiderados, sem afirmar que IP equivale a dispositivo físico.

## Escopo do artigo

O núcleo compara árvores, boosting e redes compactas; reproduz criticamente a suficiência atribuída ao Random Forest; e testa o valor próprio de contexto relacional quando defensável. A execução local versus borda será avaliada depois que os modelos forem congelados.

Ataques desconhecidos, aprendizado federado, votação bizantina e Kubernetes não pertencem ao núcleo inicial. Docker e `tc-netem` poderão compor o benchmark de sistemas; Kubernetes só será reconsiderado se houver uma pergunta experimental que exija orquestração e tolerância a falhas.

## Exposição prévia e limites

Os autores do projeto já examinaram o dataset completo e notebooks anteriores. O reinício do código não torna o UAVIDS-2025 um conjunto historicamente intocado. O protocolo, os folds persistidos e a separação entre desenvolvimento e teste reduzirão decisões adaptadas aos resultados, mas não apagam essa exposição.

Permanecem manuais e pendentes: equipamento e horas disponíveis, publicação-alvo, licença exibida na fonte canônica, origem/licença dos notebooks de terceiros e respostas dos autores sobre geração, sessões, timestamps e disponibilidade dos atributos.
