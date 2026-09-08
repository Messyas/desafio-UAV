# Protocolo do benchmark Docker local v2

Data de congelamento: 8 de setembro de 2026, antes da execução.

## Pergunta e escopo

O experimento mede o custo de servir os modelos tabulares selecionados como uma requisição HTTP local dentro de um container com recursos limitados. Ele compara XGBoost e Random Forest usando exatamente os artefatos congelados em `deployment_candidates_v1`.

CNN, GNN, MLP e stacking não participam desta etapa. A comparação preditiva usada para selecionar os candidatos permanece a registrada nos protocolos anteriores; o benchmark de sistemas não recalcula qualidade nos dados usados para congelar os modelos.

## Ambiente e limites

- Plataforma: containers Linux/amd64 executados pelo Docker Desktop/WSL2 em host Windows.
- Um container separado por modelo.
- Limite: 0,5 CPU, 512 MiB de memória e 256 processos/threads.
- Quatro threads declaradas para as bibliotecas numéricas, sob a quota total de CPU do container.
- Sistema de arquivos somente leitura, exceto `/tmp` temporário.
- Porta publicada apenas em `127.0.0.1`.
- Mesma imagem, serviço, schema, entradas e configuração de carga para os dois modelos.
- `TCP_NODELAY` habilitado nos sockets aceitos pelo servidor para evitar o atraso artificial de aproximadamente 40 ms observado no piloto v1 com mensagens pequenas e conexões persistentes.

Esses limites controlam recursos, mas não reproduzem a arquitetura, instruções, memória ou consumo energético de Raspberry Pi, Jetson ou outro computador embarcado.

## Fronteiras de tempo

### Latência HTTP do cliente

- Início: imediatamente antes de enviar uma requisição HTTP já serializada.
- Fim: após receber e ler integralmente a resposta.
- Inclui: transporte local, desserialização no servidor, espera pela trava/fila, `predict_proba`, conversão da resposta e serialização HTTP.
- Exclui: seleção do registro e serialização JSON do corpo no cliente, extração do fluxo de rede, cálculo dos 18 atributos e decisão de mitigação.

### Tempo interno do modelo

- Início: após validação do tensor e aquisição da trava do modelo.
- Fim: retorno de `predict_proba`.
- A espera pela trava é registrada separadamente.

## Carga

- Semente: `20260907`, com deslocamento fixo por modelo.
- Entradas: linhas amostradas do mesmo CSV identificado no manifesto dos modelos; rótulos não são enviados ao serviço.
- Aquecimento: 200 requisições individuais, excluídas das métricas.
- Latência individual: cinco repetições de 1.000 requisições sequenciais, reutilizando a conexão HTTP.
- Lotes: tamanhos 1, 32, 256 e 1.024; cinco repetições de 30 chamadas por tamanho.
- Throughput: concorrências 1, 4 e 8; cinco repetições de 300 requisições individuais por nível.
- Recursos: amostras de `docker stats` a cada aproximadamente 0,5 s durante a carga.

São preservadas as durações individuais, os tempos internos, os tempos de espera, os resultados por repetição e as amostras de recursos. P50, P95, P99, média, desvio, máximo e requisições por segundo são derivados desses registros.

## Integridade e falhas

- Dataset, schema e modelos devem coincidir com os hashes do manifesto congelado.
- O serviço executa um smoke test de forma e soma das probabilidades antes de ficar disponível.
- Toda resposta é validada quanto ao status e tamanho do lote.
- Os limites efetivamente aplicados são obtidos por `docker inspect` e persistidos.
- ID da imagem, versão do Docker, host e configuração são persistidos no manifesto.
- Ausência de amostras de recursos, hash divergente, resposta inválida ou container não saudável interrompe a rodada; a falha não vira uma métrica numérica.

## Limites de interpretação

O estudo mede atendimento de vetores de fluxo prontos em loopback local. Não mede rede entre máquinas, mobilidade UAV, canal sem fio, perda de pacotes, energia, bateria, ARM, tempo até detecção ou generalização preditiva. O resultado pode sustentar apenas afirmações sobre custo relativo nesta bancada Docker local.

## Piloto descartado

Uma primeira execução, identificada como `docker_local_v1`, apresentou aproximadamente 45 ms constantes entre o tempo interno do servidor e o tempo observado pelo cliente para ambos os modelos. O padrão foi atribuído à interação Nagle/delayed ACK do servidor HTTP básico em conexões persistentes pequenas. Essa rodada permanece local para auditoria, mas não será usada como resultado do artigo. A v2 foi congelada antes da repetição e difere apenas pela ativação explícita de `TCP_NODELAY` e pelos identificadores de configuração/imagem.
