# Ablação pareada e revisão acadêmica — v4

Congelamento: 26 de setembro de 2026. Estudo exploratório; o dataset, os folds e resultados anteriores já foram examinados. O arquivo `configs/feature_ablation_v4.json` define o orçamento; não é um protocolo confirmatório registrado antes de qualquer exposição aos dados.

## Pergunta e controles

Medir quanto três razões derivadas alteram a classificação das cinco classes do UAVIDS-2025 nos protocolos S0/S1/S2. RF e XGBoost usam exatamente os parâmetros de `predictive_baseline_v1.json`, cuja identidade é verificada. O RF de estabilidade histórica, com 240 árvores e folha mínima 2, não substitui este controle de 200 árvores e folha mínima 1.

Todos os braços usam os mesmos índices, classes, seed e contrato de pré-processamento. A0 é retreinado neste ambiente, sem reaproveitar predições históricas. A configuração original permanece intacta.
`tools/verify_control_parity.py` compara, após a grade v4 completa, as 30 predições A0 com os controles homólogos da baseline e registra hashes e igualdade exata. Igualdade valida equivalência numérica neste dataset/ambiente, não cria evidência independente.

| Condição | Atributos |
|---|---|
| A0 | 18 originais, excluindo FlowID, SrcAddr, DstAddr e Protocol |
| A1 | A0 + LostPackets/TxPackets |
| A2 | A0 + RxBytes/TxBytes |
| A3 | A0 + Throughput/Kbps/AverageHopCount |
| A4 | A0 + as três razões |

Denominador ≤0 ou overflow gera NaN; não se acrescenta epsilon. Razões A1/A2 são adimensionais; A3 tem unidade Kbps/hop. Não se recorta razão em [0,1]. `tx_efficiency` é um nome operacional para a razão, não medida comprovada de eficiência energética.

Os atributos brutos precisam ser finitos, como no CSV auditado. Derivadas são calculadas dentro do pipeline e imputadas por mediana ajustada exclusivamente no treino externo. O mesmo imputer está presente em A0. Uma derivada inteiramente ausente no treino é preservada e preenchida com 0 por `keep_empty_features=True`; as estatísticas de treinamento ficam no registro do job. Mudança desta política exige novo experimento.

A3 tem 38.501 denominadores não positivos neste CSV (aproximadamente 31,5% dos exemplos), enquanto A1/A2 não geram ausentes. A3 precisa ser interpretada junto à sua cobertura e à imputação; não assumir que mede capacidade real por salto em todos os fluxos. Diagnósticos globais e por classe são descritivos e não fornecem medianas ao pipeline.

API: [SimpleImputer 1.5](https://scikit-learn.org/1.5/modules/generated/sklearn.impute.SimpleImputer.html). `DerivedFeatures` segue a interface clonável de estimadores e retorna a ordem congelada dos atributos.

## Orçamento e ordem

- Etapa 1: S2, 2 modelos × 5 folds × 5 condições × 1 seed = 50 jobs.
- Etapa 2: S0/S1 completos, mais 100 jobs. Painel v4 completo = 150 jobs.
- Seed de treinamento: 20260907; quatro threads; sem tuning nem parada guiada pelo teste.
- Seleções de linha de comando controlam somente a execução; não alteram a grade congelada ou transformam uma amostra parcial em experimento completo.
- Resultados negativos, avisos e falhas permanecem visíveis. A retomada usa hashes, sem retreinar silenciosamente um artefato completo corrompido.

O executor verifica alinhamento de row_id, FlowID e rótulos, cobertura da partição, presença das cinco classes no treino/teste e exclusividade dos grupos. S1 agrupa assinaturas numéricas exatas; S2 agrupa SrcAddr. Essas unidades não identificam execuções independentes nem aeronaves físicas. S2 pode compartilhar destinos e assinaturas entre treino/teste: consultar os diagnósticos de sobreposição da auditoria.

`tools/run_ablation.py` usa o mesmo executor e conserva diagnósticos de invocações que falharam em research_artifacts/failures/. O executor direto também deixa manifesto parcial e exceção; usar o wrapper no restante das execuções para persistir o traceback.

Antes do primeiro ajuste, `frozen_protocol.json` preserva configuração, checksums de dados/splits/código e ambiente. Retomada recusa alterações. Falhas deixam manifesto parcial; falta de um único fold impede analisar a célula como OOF completa. Arquivos de treinamento históricos não são editados pela análise.

## Estabilidade e sensibilidade

`feature_ablation_stability_v5.json`: todas as condições A0–A4 em S2, ambos os modelos, cinco folds e seeds 20260907/08/09: 150 jobs próprios. Não repetir somente a condição que aparentar ganhar. As sementes são descritas separadamente e não tratadas como populações independentes. O controle A0 desta rodada também é ajustado novamente.
`seed_variation.csv` resume média, desvio padrão descritivo e amplitude de F1 OOF e deltas pareados entre seeds, sem intervalo ou teste que presuma amostras independentes.

`pdr_sensitivity_v6.json`: 10 jobs S2, ambos os modelos e apenas os 18 atributos, com PacketDropRate recortado em [0,1]. A referência é A0 v4 original. `sensitivity_analysis.py` exige igualdade de modelos/parâmetros, atributos, classes, folds, seeds, threads, dados, splits, código de treinamento e ambiente. Esse recorte é análise secundária, não correção presumida do simulador.

## Auditoria de redundância

`tools/audit_derived_features.py` produz diagnóstico descritivo, não estatísticas usadas no treinamento. No CSV canônico, loss_ratio e PacketDropRate têm correlação quase 1; 122.148 de 122.171 linhas são próximas sob atol=1e-8 e rtol=1e-5. A1 pode ser essencialmente redundante. Medir ganho não estabelece novidade, informação adicional ou causalidade; arredondamento e alteração do espaço de seleção de atributos de árvores também podem alterar predições.

## Métricas e bootstrap pareado

F1-macro usa as cinco classes fixas e zero_division=0. A análise verifica predições, probabilidade, identidade, cobertura e métricas salvas por job. Reporta F1 OOF concatenado, média/SD descritivos dos folds, balanced accuracy, log loss, falso alarme (normal→ataque), ataque perdido (ataque→normal), precisão/recall/F1/suporte por classe e confusão absoluta.
`confusion_normalized.csv` divide cada célula pelo suporte da sua classe verdadeira, por protocolo/modelo/seed/condição, com zero quando o denominador é zero; não mistura populações nem seeds.

Comparações A1–A4 versus A0: diferença absoluta de F1-macro, bootstrap percentile de 2.000 réplicas, 95%, RNG 20260926. Cada réplica sorteia grupos inteiros com reposição e preserva todos os fluxos de um grupo; usa o mesmo sorteio nos dois braços. Grupos têm igual probabilidade de sorteio e os fluxos dos grupos sorteados mantêm seu peso nas métricas. Folds não são unidades independentes para teste t.

- S2: SrcAddr como unidade operacional de reamostragem.
- S1: assinatura numérica original como unidade; isto não controla automaticamente dependência entre assinaturas da mesma execução/origem.
- S0: reamostragem por SrcAddr explicitamente identificada como sensibilidade sobre split aleatório; não equivale a avaliação de origens inéditas.

Uma classe ausente em uma réplica conserva F1=0 na média fixa; a quantidade dessas réplicas é reportada. Não se descarta a réplica para condicionar artificialmente o intervalo. Implementação agrega confusões por grupo e limita memória para S1.

Os intervalos são condicionais a predições OOF fixas e às unidades escolhidas. Dependência entre modelos ajustados em treinos sobrepostos e entre grupos de uma mesma simulação não desaparece. Não são intervalos da incerteza completa de retreinamento ou generalização a novos cenários. Não há margem de equivalência pré-definida, teste confirmatório, ajuste de multiplicidade ou escolha de vencedor pelo intervalo; todas as comparações são exploratórias.

Quando dois ou mais protocolos estão completos, `protocol_comparisons.csv` contrasta S1−S0, S2−S0 e S2−S1 no mesmo par modelo/condição/seed. Para esses contrastes, SrcAddr é a unidade de reamostragem comum, como sensibilidade. Regimes de treinamento e padrões de sobreposição mudam juntos; a diferença observada não isola uma causa nem cria avaliação independente.

## Rastreabilidade para a redação posterior

`analysis_manifest.json` vincula tabelas à configuração, dataset, partições, predições e código de análise. `build_ablation_report.py` cria gráficos PDF/SVG/PNG e relatório factual a partir das tabelas verificadas. `package_research.py` cria um ZIP local com hashes, protocolo, código, folds, predições e relatórios; não inclui o CSV bruto e não publica nada.

O painel completo precisa de S0/S1/S2. Um relatório somente S2 registra esse escopo e a incompletude do painel integral. Antes da submissão: revisar literatura, semântica/disponibilidade causal dos atributos, licenças, reprodução em ambiente limpo e adequação ao veículo. Não reescrever resultados do DOCX antes de concluir a análise; não prometer bateria, zero-day, ARM ou detecção online a partir deste experimento.
