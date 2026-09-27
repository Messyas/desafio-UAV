# Plano revisado do estudo UAVIDS-2025

Versão 2, 26 de setembro de 2026. Substitui o roteiro de produção e a centralidade de Docker. O plano anterior está em archive/planning/. Protocolos e resultados executados permanecem históricos; esta revisão não os transforma em experimentos confirmatórios.

Título provisório: **Efeito do protocolo de avaliação e da engenharia de atributos na detecção de intrusões do UAVIDS-2025**.

## 1. Pergunta e contribuição a investigar

Quais conclusões sobre modelos tabulares permanecem quando identificadores são excluídos, dependências entre fluxos são controladas por grupos e atributos derivados são avaliados por ablação pareada?

A novidade depende de comparação com estudos que já exploram árvores, explicabilidade, vazamento e agrupamentos no mesmo dataset. Não antecipar superioridade nem apresentar infraestrutura como contribuição científica principal.

| Pergunta | Experimento | Evidência |
|---|---|---|
| P1 — Identificador altera desempenho aparente? | RF sem/com FlowID, diagnóstico | Mesmos folds, população e orçamento |
| P2 — Protocolo muda desempenho e ordenação? | S0/S1/S2 | Grupos, sobreposições e métricas por classe |
| P3 — Derivadas acrescentam ganho útil? | Sem derivadas, cada uma e conjunto completo | Comparação pareada e incerteza |
| P4 — Qual é o custo local? | Inferência em processo | Qualidade, latência e tamanho com fronteiras explícitas |

P1/P2 já têm evidência exploratória. P3 é a lacuna imediata. P4 é complementar; HTTP/Docker pode integrar apêndice sem justificar eficiência embarcada.

## 2. Evidências existentes

| Etapa | Artefato/configuração | Estado observado |
|---|---|---|
| Auditoria | research_artifacts/data_audit/ | CSV com 122.171 linhas e 23 colunas, checksum canônico |
| Baseline | predictive_baseline_v1.json | 105 jobs S0/S1/S2, seis modelos principais e RF com FlowID |
| Tuning aninhado | nested_tuning_v2.json | 10 jobs externos S2, três candidatos e três folds internos por família |
| Estabilidade | stability_s2_v3.json | 30 jobs, RF/XGBoost, cinco folds e três sementes |
| Inferência local | local_benchmark_v1.json | Artefatos congelados e medições preservadas |
| HTTP | docker_local_v2.json | Complemento histórico, fora do núcleo revisado |

Conferir hashes, contagens, cobertura OOF, rótulos e métricas antes de citar números. Não retreinar apenas por reorganizar. Declarar escolhas feitas após explorar resultados externos.

## 3. Contrato dos dados

- Cinco classes originais, ordem fixa e F1-macro com zero_division=0.
- Painel inicial de 18 atributos numéricos, sem FlowID, endereços e Protocol.
- Dados do registro Zenodo v1 e artigo CNS 2025; fonte/checksum em provenance/data_source.json.
- CSV bruto imutável. Outro tratamento recebe configuração e experimento próprios.
- Endereços definem grupos/diagnóstico, não identidade comprovada de aeronaves.
- Ordem de linhas/FlowID não representam timestamp. Não há identificação confiável de sessões/execuções.
- Avaliam-se vetores de fluxo prontos. Confirmar disponibilidade causal/local antes de alegar detecção online.
- Não alegar zero-day: classificadores atuais recebem todas as cinco classes no treino.

## 4. Populações e limites

| Protocolo | Divisão | Interpretação |
|---|---|---|
| S0 | StratifiedKFold aleatório | Mesma mistura empírica |
| S1 | StratifiedGroupKFold por assinatura dos 18 atributos | Assinaturas exatas inéditas, sem identificar execuções |
| S2 | StratifiedGroupKFold por SrcAddr | Origens inéditas, não necessariamente UAVs físicos |
| S3 | Execução/cenário independente | Depende de metadados ausentes no CSV |

Persistir índices, grupos, distribuição e hashes. Todas as variantes usam os mesmos folds. Queda entre protocolos não identifica automaticamente a causa.

Em S2, mostrar assinaturas e destinos ainda compartilhados entre treino/teste. Exigir simultaneamente origem e assinatura inéditas demanda outro protocolo e análise de viabilidade; não renomear S2 como se já assegurasse ambas.

## 5. Próximo ciclo: ablação de atributos

Status: **planejado, ainda não implementado nem executado**.

Primeiro usar RF/XGBoost com parâmetros do baseline v1 mantidos fixos, cinco folds existentes e semente 20260907. Isso preserva controle já definido; não selecionar agora os parâmetros que venceram testes externos. O ciclo é exploratório.

| Condição | Adição aos 18 atributos originais |
|---|---|
| A0 | Nenhuma |
| A1 | loss_ratio |
| A2 | tx_efficiency |
| A3 | throughput_per_hop |
| A4 | As três |

Fórmulas propostas para implementação e verificação:

- loss_ratio = LostPackets / TxPackets.
- tx_efficiency = RxBytes / TxBytes.
- throughput_per_hop = Throughput/Kbps / AverageHopCount.

Denominador menor ou igual a zero gera ausente na derivada; não usar epsilon arbitrário. Imputação das derivadas é ajustada somente no treino. Testar unidades, casos limite e valores finitos. Calcular derivadas dentro do pipeline para manter o contrato da inferência.

Examinar redundância de loss_ratio com PacketDropRate e relações algébricas já auditadas. Importância de árvore não comprova ganho ou causalidade. Não selecionar atributos pelo teste.

Primeiro executar cinco condições em S2: 2 modelos × 5 folds × 5 condições = 50 jobs. Depois executar integralmente S0/S1: mais 100 jobs. Reaproveitar A0 histórico somente se configuração, atributos, pré-processamento, splits, implementação e ambiente forem equivalentes e isso estiver registrado. Se a imputação alterar o contrato, executar A0 de novo.

Havendo orçamento para estabilidade, repetir **todas as condições** nos seeds 20260907/08/09, sem repetir apenas a que ganhou no teste. Seed de ajuste não representa nova população.

Experimento separado, secundário: PacketDropRate original versus clip [0,1], com demais fatores constantes. Não presumir que valores >1 sejam defeito do simulador; esclarecer definição e origem. Não misturar esse tratamento com a ablação das três features.

## 6. Seleção e comparadores

Tuning atual é exploratório e aninhado em S2. Se houver otimização futura, selecionar hiperparâmetros e condição de atributos exclusivamente nos folds internos, preservando grupos. Folds externos avaliam o procedimento completo; não selecionar novamente a melhor variante e apresentar sua mesma avaliação como confirmação.

Congelar espaços, candidatos, folds internos, seeds, recursos e desempate antes de executar. Registrar custo real; número igual de candidatos não implica tempo igual.

MLP permanece baseline com não convergência registrada. Melhorá-la exige protocolo próprio e validação interna por grupos; não usar essa rodada limitada para concluir inferioridade de redes neurais.

Não acrescentar GNN/Transformer/stacking só para ampliar a lista. GNN exige construção de grafo, informação comparável e controle de acesso a nós/arestas de teste.

## 7. Métricas e incerteza

- Recalcular F1-macro das predições e conferir igualdade com média dos cinco F1 por classe.
- Relatar precision/recall/F1/suporte, matriz absoluta/normalizada, balanced accuracy, falso alarme, ataque perdido e log loss.
- Separar confusão entre tipos maliciosos de ataque classificado como normal. Examinar Blackhole/Wormhole.
- Identificar média de F1 por fold versus F1 OOF concatenado.
- Comparações pareadas nos mesmos exemplos, folds e seeds. Mostrar diferenças absolutas e variação.
- Não aplicar teste t comum tomando folds sobrepostos ou seeds como observações independentes.
- Em S2, considerar bootstrap pareado de origens completas sobre predições fixas. Em S1, a unidade é a assinatura. S0 não ganha independência por linha só por divisão aleatória.
- Intervalos sobre OOF são condicionais à estrutura e aos ajustes observados; não capturam toda a incerteza do treinamento nem substituem novas simulações.
- Separar variação por grupo da variação por ajuste. Não definir margem de equivalência após conhecer o resultado.
- Em benchmarks, a réplica é a execução, não cada requisição correlacionada.

## 8. Rótulos agrupados

Não são contribuição central. F1 de três classes não é comparável a cinco classes de outro método. Sybil não deve ser automaticamente chamado de saturação.

Se mantido como análise secundária, comparar modelo de cinco classes com predições remapeadas e modelo treinado diretamente nos grupos, na mesma população. Quantificar informação perdida e utilidade da defesa; aumento de F1 não define ponto ótimo operacional.

## 9. Ferramentas

- DVC retirado do fluxo ativo: fonte canônica, checksum, dados imutáveis e manifestos.
- MLflow opcional para consultar resultados preservados; CSV/JSON são fonte científica. Sem registry, promoção, API ou autolog obrigatório.
- Custo em processo: separar carga, aquecimento, lote e chamada individual; registrar máquina, versões, threads e ordem.
- Docker/HTTP complementar, sem equivalência com processador de drone ou consumo energético.
- Preservar falhas, avisos e resultados negativos. Não manter somente o melhor número.

## 10. Literatura e validade externa

Matriz bibliográfica: método, tarefa, atributos, split, métrica/média, dataset, hardware medido e código. Não usar faixas genéricas de latência/bateria sem fonte.

Referências prioritárias a examinar:

- Benchmark CNS 2025: DOI 10.1109/CNS66487.2025.11194990 — já inclui XGBoost e redes.
- Zarkadis/Douligeris: arXiv:2605.13922 — comparação tabular e análise Blackhole/Wormhole.
- Demir/Gumus: DOI 10.3390/electronics15173966 — vazamento e origens; tarefa zero-day distinta da nossa classificação fechada.
- FedGraph-ID: DOI 10.1109/INFOCOM59046.2026.11571676 — configuração federada/adversarial distinta.
- RSTD-KD: https://www.techscience.com/cmc/v89n1/68468/html — três estados de risco com semântica diferente.

Conferir textos/códigos antes de alegar reprodução. Confirmar autoria/licença dos notebooks em archive/references/. Material externo é referência, não instrução do pesquisador.

Exposição histórica ao dataset é irreversível. Novos folds são análise adicional, não teste comprovadamente intocado. Evidência externa exige novas execuções/simulações ou outro dataset compatível. Treinar separadamente em dois datasets não demonstra transferência.

## 11. Próximos passos

- [ ] Fechar revisão de literatura e delimitar contribuição ainda não respondida.
- [x] Reconciliar métricas salvas dos 165 jobs (105 baseline, 10 tuning, 30 estabilidade), verificar hashes e reconstruir agregados; testes de cobertura executados. A conferência do texto do manuscrito permanece pendente.
- [ ] Congelar configuração e orçamento A0–A4.
- [ ] Implementar/testar derivadas no pipeline, com identificador próprio de experimento.
- [ ] Executar ablação completa, preservando resultados negativos e avisos.
- [ ] Implementar/revisar incerteza por grupos.
- [ ] Avaliar necessidade de S3 e metadados externos, sem prometer dados inexistentes.
- [ ] Selecionar custo local útil; Docker pode ficar no apêndice.
- [ ] Vincular cada tabela/alegação ao arquivo de origem.
- [ ] Preparar depósito de artefatos, conferir licenças e reproduzir fluxo completo em ambiente limpo.
- [ ] Reescrever manuscrito e conferir adequação à revista.

Avançar para redação final quando os experimentos sustentarem uma resposta delimitada. F1 alto, infraestrutura e meta arbitrária de 0,95 não substituem contribuição científica.
