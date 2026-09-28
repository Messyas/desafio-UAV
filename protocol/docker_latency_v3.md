# Comparação de latência com cinco modelos — v3

Preparação: 27 de setembro de 2026, antes das novas medições. Estudo exploratório, com qualidade preditiva já conhecida. Configurações históricas e resultados Docker v1/v2 permanecem preservados.

## Pergunta

Comparar custo de inferência e atendimento HTTP de regressão logística, MLP compacta (64/32), XGBoost, Random Forest e Extra Trees sob quota de 0,5 CPU e 512 MiB. Todos usam 18 atributos e cinco probabilidades; escalonamento de regressão logística e MLP faz parte do pipeline cronometrado. Não incluir RF com FlowID, usado apenas no diagnóstico de artefatos. Não incluir CNN/GNN sem representação e protocolo de treinamento adequados a elas.

Modelos: configs/deployment_latency_v2.json, com os mesmos parâmetros da baseline preditiva v1. RF agora tem 200 árvores e folha mínima 1, diferente do artefato histórico de 240 árvores/folha 2. Isso permite vincular a comparação à baseline correspondente; não se reutilizam as latências antigas como medições dos novos artefatos. O ajuste em todos os dados serve apenas para produzir artefatos de custo, sem medir qualidade nesses mesmos dados.

Qualidade: F1-macro OOF S2 da baseline v1, não a média dos folds. A referência tem Python 3.12.10 e o novo ajuste usa 3.12.14, mantendo as versões das bibliotecas principais. A avaliação de custo e a avaliação preditiva medem objetos distintos: artefato reajustado e procedimento em folds. A tabela de comparação explicita essa diferença e verifica configurações, dados e hashes.

## Controles da medição

- Um container por modelo, mesmas dependências e serviço, CPU 0,5 e RAM 512 MiB. Swap desabilitado na nova configuração.
- Quatro threads numéricas e n_jobs=4 onde suportado, como na baseline. A quota de 0,5 CPU pode impor throttling; um resultado ruim do RF nesta condição não representa todos os ajustes possíveis de paralelismo. Uma extensão futura deve comparar 1 e 4 threads, sem misturar seus resultados.
- Mesma semente de carga para todos os modelos, produzindo a mesma sequência de entradas, aquecimento, lotes e níveis de concorrência. O benchmark histórico usava deslocamentos por modelo; esses deslocamentos não entram na nova rodada.
- Aquecimento: 200 chamadas. Individual: 5 × 1.000 chamadas. Lotes 1/32/256/1.024: 5 × 30 chamadas por tamanho. Concorrências 1/4/8: 5 × 300 requisições por nível.
- Mesmas fronteiras do protocolo Docker v2: HTTP medido do envio do corpo pré-serializado até a leitura da resposta; inferência interna medida em predict_proba, incluindo etapas do pipeline. Fila registrada separadamente. TCP_NODELAY permanece habilitado.
- Reportar P50/P95/P99, throughput por concorrência, tamanho de artefato e amostras de memória/CPU. Manter registros por repetição; quantis agregados são descritivos, não intervalos de generalização para outros hosts.
- Ordem fixa declarada: regressão logística, MLP, XGBoost, RF e Extra Trees. Ela é uma limitação: uma única sessão e ordem não controlam deriva térmica ou carga do host. Para afirmações fortes de ranking, repetir sessões com ordem alternada/randomizada e novos IDs, preservando as mesmas cargas.

## Falhas e interpretação

Timeout, falta de memória ou falha de inicialização são resultados de viabilidade, não latência zero. O executor salva estado/logs do container antes de removê-lo, registra a falha e continua com os demais modelos. Um painel com falhas fica parcial; uma tabela marca explicitamente resultados pendentes e falhas.

A medição não inclui coleta de fluxos e cálculo dos atributos, e não demonstra detecção online, energia, rádio ou comportamento em ARM. O resultado esperado é uma comparação de qualidade/custo nesta bancada, não uma declaração de que o modelo mais rápido é sempre o melhor.

## Execução

```powershell
.\.venv-research\Scripts\python.exe src\uavids_study\freeze_models.py --config configs\deployment_latency_v2.json
.\.venv-research\Scripts\python.exe src\uavids_study\docker_benchmark.py --config configs\docker_latency_v3.json
.\.venv-research\Scripts\python.exe tools\build_latency_comparison.py
```

Docker Desktop precisa estar iniciado com o engine Linux disponível. A preparação não significa que a medição foi executada. Resultados ficam em benchmarks/docker_latency_v3/ e reports/docker_latency_v3/. O artigo só deve receber valores desta rodada depois de sua execução e conferência; não substituir por latências estimadas.
