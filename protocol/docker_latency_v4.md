# Comparação de latência com cinco modelos — v4

Revisão exploratória de 27 de setembro de 2026, após a execução v3. Mantém os cinco artefatos congelados em deployment_latency_v2 e a avaliação preditiva OOF S2 da baseline v1. A v3 e suas falhas permanecem preservadas.

Na v3, o RF foi encerrado por falta de memória durante o carregamento. A implementação criava uma cópia completa do pickle antes de desserializar. A v4 usa pickle.load sobre o arquivo aberto, reduzindo uma cópia evitável. Isso não garante que todos os modelos caibam em 512 MiB.

A v4 fixa uma thread por modelo, sob a mesma quota de 0,5 CPU e 512 MiB sem swap. Define OMP, OpenBLAS, MKL e NumExpr e substitui n_jobs dos estimadores após carregar. Esse ajuste modifica paralelismo de inferência, não pesos aprendidos; a semente e as quatro threads usadas no ajuste dos artefatos permanecem registradas. A qualidade OOF descreve o procedimento da baseline, não uma nova avaliação do artefato ajustado em todos os dados.

Todos os modelos são novamente medidos nesta versão. Não misturar quantis de v3 e v4. Como carregamento e paralelismo mudaram juntos, o contraste entre versões não isola causalmente nenhum desses fatores. A versão é posterior a resultados conhecidos e não confirmatória.

A carga, ordem dos cinco modelos, fronteiras de tempo, aquecimento, repetições e métricas são os mesmos de protocol/docker_latency_v3.md. Ordens/sessões adicionais seriam necessárias para interpretar pequenas diferenças como um ranking estável. Falhas continuam sendo resultados de viabilidade; não recebem latência numérica.

```powershell
.\.venv-research\Scripts\python.exe src\uavids_study\docker_benchmark.py --config configs\docker_latency_v4.json
.\.venv-research\Scripts\python.exe tools\build_latency_comparison.py --config configs\docker_latency_v4.json
```

Resultados em benchmarks/docker_latency_v4/ e reports/docker_latency_v4/. Medem vetores prontos em HTTP/loopback, sem coleta, rádio, ARM ou energia.
