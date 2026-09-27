# Escopo vigente do estudo

Revisão: 26 de setembro de 2026. A versão de 8 de setembro centralizava RF/XGBoost e Docker. Mudança registrada em deviations.md; configurações anteriores não foram alteradas retroativamente.

## Tarefa e entrada

- Cinco classes originais na ordem registrada em configs/.
- F1-macro primário, acompanhado de métricas por classe, falso alarme e ataque perdido.
- Painel inicial: 18 atributos numéricos sem FlowID, endereços ou Protocol.
- Endereços/assinaturas são metadados de grupos e diagnóstico.
- Classificação de vetores de fluxo prontos; disponibilidade causal/local não confirmada.

## Populações

- S0: divisão estratificada aleatória da mistura observada.
- S1: assinaturas numéricas exatas inéditas; não equivale a sessões independentes.
- S2: endereços de origem inéditos; não equivale a UAVs físicos nem garante destinos/assinaturas inéditos.
- S3: execuções/cenários novos, condicionado a metadados confiáveis ausentes no CSV.

Núcleo: identificadores, sensibilidade ao protocolo e contribuição das derivadas. RF/XGBoost são candidatos principais; demais modelos existentes são baselines exploratórios. Nova ablação ainda não implementada nem executada.

## Infraestrutura

DVC e promoção saíram do fluxo ativo. MLflow é tracking opcional. Custo em processo é complementar. Docker/HTTP permanece complemento histórico sem ser requisito do núcleo.

CNN, GNN, modelos temporais, stacking, Kubernetes, emulação de rádio, energia, mitigação automática, federado e zero-day não sustentam conclusões principais. Agrupamentos de classes exigem justificativa operacional e avaliação separada.

## Exposição e alterações

Dataset e resultados externos dos folds já foram examinados. Código novo ou seeds novos não criam avaliação confirmatória intocada. Extensões permanecem exploratórias, com decisões registradas antes de executar.

Novo método/população recebe identificador, hashes e desvio próprios. Não misturar tarefas, médias de métricas ou protocolos incompatíveis em alegação de superioridade.
