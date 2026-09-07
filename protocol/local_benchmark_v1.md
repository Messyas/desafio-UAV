# Protocolo do benchmark local v1

Data: 7 de setembro de 2026. Status: piloto de medição, anterior ao benchmark Docker final.

## Fronteira medida

- Entrada pronta: matriz NumPy `float64` com 18 atributos na ordem congelada.
- Início: imediatamente antes de `predict_proba` do pipeline carregado.
- Fim: retorno das cinco probabilidades.
- Exclui: leitura do CSV, extração de fluxo, serialização, rede, fila e decisão operacional.

## Procedimento

- Um processo separado por modelo para reduzir interferência de memória entre artefatos.
- Quatro threads permitidas, registradas, sem fixação de afinidade ou quota de CPU.
- 200 chamadas de aquecimento, não incluídas nas métricas.
- Cinco repetições; 1.000 chamadas individuais por repetição.
- Lotes 1, 32, 256 e 1.024, com 30 chamadas por repetição.
- Entradas sorteadas deterministicamente do CSV; os rótulos não são carregados pelo benchmark.
- Preservar cada duração individual. Reportar P50/P95/P99, média, máximo e vazão.

## Limites

O host Windows e sua carga não estão dedicados. Batch 1 mede chamada em processo, não requisição. O tempo por linha em lote é amortizado. RSS antes/depois do carregamento é diagnóstico e não representa pico de memória. Esta etapa não mede energia, tempo até detectar ataque ou latência de rede.
