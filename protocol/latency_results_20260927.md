# Resultados da comparação ampliada de latência

Execução: 27 de setembro de 2026. Painel primário de custo: docker_latency_v4. Todos os cinco candidatos foram tentados; quatro completaram a medição e Extra Trees foi encerrado por falta de memória ao carregar. Não há latência numérica para a falha.

## Configuração e origem da qualidade

Docker Desktop com engine Linux, quota de 0,5 CPU, 512 MiB sem swap e uma thread por modelo. Entradas idênticas, 200 chamadas de aquecimento, 5.000 chamadas individuais, 600 chamadas em lotes e 4.500 requisições de throughput por modelo medido. Cada modelo foi executado separadamente; a ordem foi fixa, em uma sessão.

Os artefatos deployment_latency_v2 foram ajustados em todos os dados somente para medição de custo. F1-macro vem da avaliação OOF S2 da baseline preditiva v1, com cinco folds e semente 20260907. Configurações, atributos, classes e dados correspondentes foram conferidos. Os modelos escalonados incluem o scaler no tempo interno da chamada; nenhuma qualidade foi calculada nos dados de treinamento do artefato de custo.

| Modelo | F1-macro OOF S2 | HTTP P50 (ms) | HTTP P95 (ms) | HTTP P99 (ms) | Inferência P50 (ms) | Memória máxima observada (MiB) |
|---|---:|---:|---:|---:|---:|---:|
| Regressão logística | 0,812079 | 0,923 | 1,039 | 1,132 | 0,166 | 74,89 |
| MLP compacta | 0,929876 | 0,912 | 1,034 | 1,208 | 0,170 | 73,32 |
| XGBoost | 0,952666 | 1,107 | 1,268 | 8,084 | 0,344 | 82,30 |
| Random Forest | 0,950677 | 5,856 | 51,302 | 52,782 | 4,941 | 489,00 |
| Extra Trees | 0,949486 | — | — | — | — | — |

Fonte completa: reports/docker_latency_v4/quality_latency_comparison.csv e summaries em benchmarks/docker_latency_v4/. F1 em escala 0–1; latência em milissegundos. Memória é o máximo das amostras de docker stats durante a carga, não o pico exato de alocação.

## Interpretação delimitada

A regressão logística é rápida, mas tem menor F1. A MLP apresenta latência próxima à da regressão e F1 maior; pequenas diferenças de latência entre elas não estabelecem ranking estável. XGBoost tem o maior F1 deste painel, mediana HTTP próxima a 1,1 ms e menor memória observada que RF. RF apresenta cauda de latência maior e fica próximo do limite de RAM. A quota de CPU pode produzir throttling, mas esta rodada não isolou causalmente seu efeito.

Extra Trees tem artefato de aproximadamente 583,68 MiB e foi encerrado com OOMKilled=true e código 137 antes de ficar pronto. Isso descreve a inviabilidade dessa configuração de modelo/carregador/limite. Não significa que toda configuração de Extra Trees precise dessa memória. Uma versão menor exigiria novo protocolo, avaliação preditiva correspondente e outra medição.

Os valores não são detecção ponta a ponta: excluem extração de fluxos e cálculo dos atributos. Não avaliam rádio, energia ou hardware embarcado. Uma única sessão em ordem fixa não sustenta intervalos de generalização para outros hosts nem ranking confiável de diferenças pequenas.

## Rodada v3 preservada

A v3 usou quatro threads e um carregador que materializava todo o pickle em bytes antes da desserialização. Regressão, MLP e XGBoost foram medidos; RF e Extra Trees sofreram OOM no carregamento. A v4 lê diretamente do arquivo e usa uma thread de inferência. O RF passou a carregar e concluir a medição. Não se atribui a mudança a um único fator, pois carregamento e paralelismo foram alterados juntos. A v3 é diagnóstico histórico; seus quantis não compõem a tabela v4.

## Verificações e pendências

tools/verify_latency_benchmark.py confirmou os cinco modelos tentados, hashes dos registros de custo, CPU/RAM, thread de inferência, contagens de chamadas e igualdade exata da sequência individual de entradas nos quatro modelos medidos. Resultado em reports/docker_latency_v4/measurement_checks.json. A suíte de 55 testes concluiu com OK; dez testes específicos de benchmark também passaram após os ajustes de serviço.

Antes de transformar pequenas diferenças em afirmações de artigo, repetir sessões com ordem alternada/randomizada e novos identificadores. Para medir Extra Trees sob outro limite, registrar outro perfil de recursos e executá-lo para todos os modelos, preservando a comparação comum. Não misturar medições de perfis diferentes. A redação Word ainda não foi atualizada com este complemento; utilizar os resultados verificados e este escopo ao incorporá-lo.
