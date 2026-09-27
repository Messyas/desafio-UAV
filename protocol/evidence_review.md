# Leitura crítica dos resultados da revisão experimental

Estado: 26 de setembro de 2026. Esta nota ajuda a decidir a redação posterior; não é um artigo nem uma declaração confirmatória. Toda cifra abaixo deve ser conferida no CSV e manifesto correspondentes antes de entrar no manuscrito. As três grades executadas são exploratórias, pois o dataset e os folds já eram conhecidos.

## Cobertura e rastreabilidade

- `feature_ablation_v4`: 150/150 jobs; S0/S1/S2, RF/XGBoost, A0–A4, cinco folds e seed 20260907. Fonte: `results/feature_ablation_v4/experiment_manifest.json` e `reports/feature_ablation_v4/analysis_manifest.json`.
- `feature_ablation_stability_v5`: 150/150 jobs; S2, os dois modelos, A0–A4, cinco folds e três seeds. Fonte: manifestos homólogos da v5.
- `pdr_sensitivity_v6`: 10/10 jobs; S2, A0, recorte de PacketDropRate; controle pareado é A0 v4. Fonte: `reports/pdr_sensitivity_v6/analysis_manifest.json`.
- A0 v4 coincide exatamente com as predições e probabilidades dos 30 jobs correspondentes da baseline histórica: `reports/feature_ablation_v4/control_parity.csv`. Os 50 jobs S2/seed 20260907 da v5 também produziram predições idênticas às da v4; isso é controle de consistência, não replicação independente.

## O que os dados mostram

F1-macro OOF de A0 na semente 20260907:

| Protocolo | RF | XGBoost |
|---|---:|---:|
| S0 | 0,955051 | 0,956326 |
| S1 | 0,953986 | 0,954612 |
| S2 | 0,950677 | 0,952666 |

Fonte: `reports/feature_ablation_v4/pooled_metrics.csv`. As diferenças de protocolo A0 são negativas para S1−S0, S2−S0 e S2−S1 nos dois modelos; os intervalos condicionais por SrcAddr em `protocol_comparisons.csv` não incluem zero. Isso mostra sensibilidade ao protocolo **neste CSV e nesses ajustes**. Não isola vazamento como causa única, nem mede cenário/voo novo. Em S2, origens não se repetem entre treino/teste, enquanto destinos e um pequeno número de assinaturas ainda podem se repetir (`research_artifacts/data_audit/fold_overlap_diagnostics.csv`).

Em S2 v4, as oito diferenças A1–A4 contra A0 (dois modelos) são pequenas e os oito intervalos condicionais incluem zero. No painel v4 inteiro, duas das 24 comparações de atributos têm intervalo abaixo de zero: A1 e A4 em RF/S1. Elas são **exploratórias, sem ajuste para multiplicidade**; não devem virar alegação de inferioridade geral. Fonte: `reports/feature_ablation_v4/paired_comparisons.csv`.

Na v5, RF/A3 teve diferença média de +0,000509 em F1-macro OOF nas três seeds (aproximadamente +0,051 ponto percentual), com deltas entre +0,000407 e +0,000576. XGBoost/A3 teve média +0,000060, com sinal diferente entre seeds. Dos 24 intervalos por seed/modelo/condição, 21 incluem zero. O intervalo da semente 20260909 para RF/A3 fica acima de zero; também há intervalos negativos isolados para RF/A2 e XGBoost/A1. Esses sinais individuais não constituem teste confirmatório, ainda mais após múltiplas inspeções. Fonte: `reports/feature_ablation_stability_v5/seed_variation.csv` e `paired_comparisons.csv`.

O recorte de PacketDropRate produziu deltas de +0,000434 (RF) e +0,000027 (XGBoost) em S2; ambos os intervalos condicionais incluem zero. Isso não demonstra que valores >1 sejam defeito do simulador nem que recortar melhore o método. Fonte: `reports/pdr_sensitivity_v6/clipping_comparisons.csv`.

As médias ocultam erros por classe. Em S2/A0, XGBoost tem recall Blackhole de 0,861241, F1 Blackhole de 0,906405 e F1 Wormhole de 0,901753. Houve 281 ataques classificados como normal e 231 normais classificados como ataque nas predições OOF, contados a partir de `reports/feature_ablation_v4/confusion_counts.csv`. A redação deve discutir o custo prático desses erros, sem inventar pesos operacionais.

## O que enfraquece a contribuição proposta

- `loss_ratio` e PacketDropRate são quase duplicados no dataset: 122.148 de 122.171 valores próximos sob a tolerância declarada e correlação de Pearson praticamente 1. A1 não sustenta uma alegação de nova informação. Fonte: `research_artifacts/derived_features/audit_manifest.json`.
- `throughput_per_hop` fica ausente em 38.501 linhas por denominador não positivo; a proporção depende da classe (por exemplo, 51,3% em Normal e 48,8% em Blackhole). A3 pode alterar decisões pelo padrão de ausência/imputação, não só por uma semântica física de throughput por salto. Fonte: `feature_diagnostics.csv` e `missing_by_class.csv` da mesma auditoria.
- Mesmo que uma diferença de F1 seja estável numericamente, sua magnitude é pequena. Não se definiu margem operacional de relevância ou equivalência antes de ver os resultados. Não chamar ausência de intervalo positivo de prova de equivalência; tampouco chamar +0,05 ponto percentual de avanço útil sem contexto.
- O benchmark original e estudos posteriores já avaliam árvores e redes em UAVIDS-2025. A novidade eventual precisa vir de pergunta/protocolo/limites bem delimitados e comparação bibliográfica honesta, não de “RF/XGBoost alcançam alto F1” ou de uma razão quase redundante.
- Intervalos de bootstrap reamostram grupos sobre predições OOF fixas. Não incorporam integralmente dependência de treinamento, sessões desconhecidas ou novos cenários. As três sementes mostram sensibilidade ao ajuste, mas não representam três populações independentes.
- O benchmark local histórico usa candidatos e parâmetros próprios. Não atribuir suas latências/tamanhos aos pipelines v4/v5. Nenhum desses testes mede bateria, ARM, rádio, decisão online ou ataque desconhecido.

## Consequência para o novo artigo

Uma contribuição defensável pode ser uma avaliação crítica e reproduzível de protocolos, identificadores e atributos em UAVIDS-2025, incluindo resultados negativos da engenharia proposta. A formulação precisa ser confrontada com a literatura real e com a política da revista pretendida. Só este dataset, com folds e comparadores já inspecionados, limita fortemente alegações de generalização e de novidade para uma revista seletiva. A evidência mais forte ainda viria de execuções/cenários independentes ou metadados confiáveis de sessão, se forem obtidos; não criar substitutos artificiais e chamá-los S3.

Antes de reescrever o DOCX: fechar a matriz bibliográfica com tarefas/splits compatíveis; revisar a semântica e a disponibilidade temporal dos atributos; discutir Blackhole/Wormhole e erros de alarme; reproduzir em ambiente limpo; conferir licenças e escolher a revista. O roteiro verificável está em `protocol/article_readiness.md`.
