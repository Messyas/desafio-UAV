# Evidências necessárias antes do novo artigo

A implementação prepara o estudo; não assegura novidade, aceitação ou classificação A2. O manuscrito histórico permanece uma referência interna. Redigir resultados somente a partir de artefatos completos e conferir a adequação à revista escolhida.

| Item | Evidência verificável | Critério de uso |
|---|---|---|
| Dados e proveniência | provenance/data_source.json; data_manifest.json | Fonte, licença e checksum canônico conferidos |
| População avaliada | split_candidates.csv.gz; diagnósticos de grupos/sobreposição | Explicitar S0/S1/S2 e o que cada um não controla |
| Atributos derivados | derived_features/feature_diagnostics.csv e missing_by_class.csv | Explicar redundância, unidades, ausência e imputação |
| Ablação principal | results/feature_ablation_v4/experiment_manifest.json | 150 jobs para discutir o painel S0/S1/S2 integral |
| Equivalência do controle | reports/feature_ablation_v4/control_parity.csv | A0 novo versus baseline, mesmas linhas e probabilidades |
| Qualidade e erros | reports/feature_ablation_v4/pooled_metrics.csv, class_metrics.csv, confusion_counts.csv, confusion_normalized.csv | F1 OOF e média dos folds distinguíveis; cinco classes mantidas |
| Diferença pareada | paired_comparisons.csv e analysis_manifest.json | Intervalos condicionais e exploratórios; sem conclusão de equivalência |
| Protocolo versus protocolo | protocol_comparisons.csv | Mesmos exemplos, sensibilidade por SrcAddr; sem atribuição causal da diferença |
| Variação de ajuste | feature_ablation_stability_v5/seed_variation.csv | Todas as condições em todas as três sementes; resumo descritivo |
| Recorte de PacketDropRate | pdr_sensitivity_v6/clipping_comparisons.csv | Sensibilidade secundária, sem presumir erro do simulador |
| Custo local | Protocolo e artefatos de benchmark próprios | Associar tempo/tamanho ao modelo/atributos exatos medidos |
| Reprodução | ZIP local com BUNDLE_MANIFEST.json | Repetir em ambiente limpo, conferir hashes e registrar novo identificador |
| Literatura | Matriz bibliográfica revisada pelos pesquisadores | Comparar somente tarefas, rótulos, atributos e splits compatíveis |

Um estágio S2 completo pode ser relatado como tal, mas não responde sozinho à comparação S0/S1/S2. Manifestos conservam a diferença entre estágio completo e painel integral completo. O exportador MLflow é uma visualização dos registros; seus gráficos não substituem a análise científica.

## Decisões de redação

- Não declarar contribuição pela criação de loss_ratio sem confrontar sua quase redundância com PacketDropRate. Ganho numérico de uma razão não comprova novo sinal, explicação causal ou melhor operação de defesa.
- A disponibilidade dos vetores de fluxo e dos denominadores precisa ser discutida antes de alegar detecção online. Estatísticas calculadas após o fluxo podem não estar disponíveis no momento de uma decisão.
- Erro Blackhole/Wormhole e ataque→normal precisa aparecer com suporte por classe, mesmo com F1-macro alto. Não ocultar resultados negativos de A1–A4.
- Comparação cinco classes versus três classes agrupadas não demonstra superioridade. Benchmark da literatura que usa FlowID ou split distinto deve ser tratado como outra configuração.
- O estudo recebe todas as cinco classes no treino; não mede ataques desconhecidos. Origem inédita não equivale automaticamente a UAV físico ou execução independente.
- Figuras e tabelas devem citar experimento, protocolo, seed, população, métrica e manifesto de origem. Registrar escolhas feitas após resultados, sem converter exploração em confirmação.
- Antes de alegar relação entre qualidade e custo das novas condições, executar um protocolo de inferência desses pipelines. Os modelos históricos de deployment_candidates_v1 usam parâmetros distintos e não são automaticamente artefatos A0/A4 desta ablação.

## Pendências humanas

Fechar revisão de literatura e contribuição ainda não respondida; revisar definições dos atributos com os autores/dicionário; identificar novos cenários ou metadados confiáveis quando viáveis; conferir licenças de dados/códigos/referências; definir a revista e suas exigências; revisar método de incerteza e adequação das unidades; executar reprodução limpa. Não preencher essas lacunas com números, cenários ou resultados supostos.
