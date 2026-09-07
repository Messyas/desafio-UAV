# Plano científico: generalização e eficiência operacional de IDS no UAVIDS-2025

Data: 7 de setembro de 2026. Versão inicial: 1.0.

Este documento especifica um projeto novo, a ser implementado do zero. Ele não valida o código antigo, não autoriza sua exclusão automática e não contém resultados novos de treinamento. Os notebooks anteriores servem apenas como material exploratório e fonte de hipóteses. DVC e a API antiga não fazem parte da contribuição científica proposta.

Título de trabalho: **Árvores, aprendizado profundo leve e contexto relacional na detecção de intrusões em UAVs: generalização e eficiência além da divisão aleatória**.

A contribuição pretendida é uma avaliação reproduzível que identifique como o protocolo de divisão dos dados, a representação dos fluxos e os recursos de comunicação afetam a escolha do detector. Superioridade, novidade e viabilidade embarcada são hipóteses a investigar, não conclusões antecipadas.

## 1. Como executar este checklist

- **[MANUAL]**: exige leitura, obtenção de material, contato externo ou decisão documentada do pesquisador.
- **[CÓDIGO]**: pode ser implementado com auxílio de IA, seguido de revisão e verificações.
- **[REVISÃO]**: conferir evidências e autorizar cientificamente a passagem de fase; não significa pedir confirmação para cada operação de programação.
- **[CONDICIONAL]**: executar somente quando as dependências indicadas existirem.
- Um item só deve ser marcado quando houver um arquivo, registro ou resultado que comprove sua conclusão.
- Falta de resposta de terceiros não é permissão nem confirmação de uma suposição. Registrar a limitação e aplicar a alternativa definida neste plano.
- Valores de orçamento, sementes, carga e recursos sugeridos aqui são pontos de partida. Devem ser congelados antes dos experimentos finais, sem alteração guiada pelos resultados de teste.

### Checklist executivo e dependências

- [ ] F0 — Definir escopo, limites de inferência e orçamento.
- [ ] F1 — Revisar literatura e registrar proveniência dos códigos.
- [ ] F2 — Obter dataset e esclarecer metadados com os autores.
- [x] F3 — Auditar dados e criar contrato de atributos. Evidência: `notebooks/research/00_auditoria_e_protocolo.ipynb` e `research_artifacts/data_audit/`.
- [ ] F4 — Congelar protocolos de divisão, tuning e análise.
- [ ] F5 — Implementar baselines e testes de integridade metodológica.
- [ ] F6 — Executar comparação preditiva e ablações.
- [ ] F7 — Congelar modelos e executar benchmark de sistemas.
- [ ] F8 — Realizar extensões apenas se justificadas.
- [ ] F9 — Analisar resultados, limitações e incertezas.
- [ ] F10 — Reproduzir a execução e escrever o artigo.

F1 e a obtenção de F2 podem avançar juntas. F5 depende de F3–F4. A preparação da bancada pode ocorrer antes, mas as medições finais de F7 dependem de modelos selecionados sem consultar o teste. Não iniciar GNN temporal, LSTM temporal ou medição de tempo até detectar ataques sem resolver a disponibilidade de tempo e sessões.

## 2. F0 — Escopo científico

### Perguntas de pesquisa

| ID | Pergunta | Evidência necessária |
|---|---|---|
| P1 | O desempenho quase perfeito atribuído ao Random Forest persiste quando identificadores e repetições são controlados e a avaliação é repetida em datasets distintos? | Reprodução fiel, reprodução corrigida, divisões por grupos e replicação independente por dataset |
| P2 | Uma rede neural compacta supera RF/Extra Trees/boosting em qualidade e custo quando recebe exatamente a mesma informação? | Comparação pareada, ablação arquitetural e medição completa de tamanho, memória e latência |
| P3 | Contexto relacional e, se houver metadados válidos, temporal acrescenta informação além de agregados tabulares equivalentes, sobretudo em Blackhole/Wormhole? | Modelos com contexto equivalente, divisões antes de janelas/grafos e ablação do contexto |
| P4 | Sob quais condições executar localmente ou na borda atende melhor às restrições? | Latência, qualidade, vazão, recursos e falhas sob carga e rede controladas |

### Três eixos centrais do artigo

Os três eixos abaixo deixam de ser extensões opcionais e passam a organizar contextualização, metodologia, resultados e discussão. A avaliação local versus borda permanece como avaliação transversal de implantação dos modelos selecionados.

#### Eixo I — Deep learning leve versus modelos tabulares

O ponto de partida é a afirmação de R4 de que uma CNN residual compacta pode combinar alta qualidade e baixo custo. O estudo deve testar essa afirmação sob a mesma informação, os mesmos splits e a mesma fronteira de medição usada para RF, Extra Trees e boosting.

- [ ] Reproduzir ou reimplementar a arquitetura de R4 com parâmetros e preprocessing confirmados.
- [ ] Comparar RF, Extra Trees, boosting, MLP compacta e CNN residual com os mesmos atributos tabulares.
- [ ] Separar forward pass, pipeline completo e requisição ponta a ponta.
- [ ] Testar se eventual vantagem neural permanece em S1/S2/S3 e em batch 1 na CPU.
- [ ] Reportar parâmetros, tamanho serializado, memória de pico, tempo de ajuste e latência; FLOPs não substituem medição.

#### Eixo II — O Random Forest é realmente suficiente em datasets distintos?

R7 relata desempenho quase perfeito de RF em Drone IDS, UAVIDS-2025 e ICSCASD-MPLC. Esse resultado será tratado como hipótese forte a reproduzir criticamente. **Treinar e testar separadamente em três datasets é replicação multi-dataset; não é transferência entre datasets.** Transferência exige treinar em uma origem e testar em outra, com taxonomia e atributos compatíveis.

- [ ] Executar reprodução fiel da metodologia relatada, sem apresentá-la como resultado próprio corrigido.
- [ ] Executar reprodução corrigida, removendo identificadores e mantendo transformações dentro dos folds.
- [ ] No UAVIDS-2025, testar explicitamente com e sem `FlowID` e quantificar a inflação de desempenho.
- [ ] Repetir o painel em cada dataset separadamente, respeitando sua unidade amostral, sessões e taxonomia.
- [ ] Não comparar apenas os F1 brutos entre datasets com número de classes e dificuldade diferentes.
- [ ] [CONDICIONAL] Executar transferência entre datasets apenas se houver interseção semanticamente válida de atributos e rótulos; documentar harmonização e perda de informação.

#### Eixo III — O contexto relacional/temporal produz ganho próprio?

**Status em 7 de setembro de 2026:** GNN e contexto temporal foram suspensos por decisão do pesquisador e pela ausência de metadados verificáveis. Os itens abaixo ficam documentados para uma eventual versão futura e não bloqueiam E1/E2 nem o benchmark de sistemas.

R2 sustenta que fluxos independentes descartam relações entre nós e evolução temporal. O estudo deve separar o benefício de **mais contexto** do benefício da **arquitetura de grafo ou sequência**.

- [ ] Criar um baseline tabular com agregados da mesma vizinhança/janela fornecida à GNN ou rede temporal.
- [ ] Comparar fluxo isolado, agregados de contexto, MLP/CNN com contexto e GNN/temporal sob a mesma divisão.
- [ ] Medir ganho específico em Blackhole/Wormhole, falsos alarmes e custo de construção do contexto.
- [ ] Dividir execuções/sessões antes de construir janelas e grafos.
- [ ] Se timestamps/sessões não forem obtidos, limitar o eixo a contexto relacional entre `SrcAddr` e `DstAddr`; não publicar uma alegação temporal baseada na ordem do CSV.
- [ ] Se nem a identidade relacional puder ser validada entre simulações, registrar que P3 não é respondível pelo artefato público e apresentar essa limitação como resultado de auditabilidade.

- [x] [MANUAL] Adotar cinco classes como tarefa principal: Normal, Blackhole, Flooding, Sybil e Wormhole.
- [x] [MANUAL] Registrar unidade predita: um registro de fluxo com atributos disponíveis no momento definido pelo experimento.
- [x] [MANUAL] Definir população de interesse: novos registros da mesma distribuição, novas origens ou novas execuções de simulação. Não tratar essas populações como equivalentes.
- [x] [MANUAL] Manter binário e quatro classes como análises secundárias, se houver orçamento.
- [x] [MANUAL] Excluir do núcleo inicial: ataques desconhecidos, aprendizado federado, votação bizantina e Kubernetes. GNN/contexto temporal pertence ao núcleo somente após passar o gate de metadados da F2; sem ele, executar apenas a variante relacional defensável.
- [ ] [MANUAL] Registrar equipamento disponível, horas de processamento, disponibilidade de Linux e acesso eventual a uma placa embarcada.
- [ ] [MANUAL] Selecionar publicação-alvo provisória e consultar exigências de dados, código, uso de IA e extensão do artigo no site oficial escolhido.
- [ ] [REVISÃO] Verificar se a contribuição ainda se diferencia dos trabalhos da F1. Não prometer publicação nem ineditismo antes desta revisão.

**Entregável:** `protocol/scope.md`, com perguntas, exclusões, orçamento, responsáveis e data.

### Resultados que também são cientificamente válidos

- Um baseline simples permanecer melhor após tuning equilibrado.
- As derivadas não acrescentarem ganho mensurável.
- O ranking mudar entre protocolos, sem que um deles represente uma verdade universal.
- A borda melhorar o custo local, mas falhar em prazo ou disponibilidade.
- O ganho do stacking ser pequeno em relação à latência ou memória adicionais.

## 3. F1 — Literatura, artigos e código de terceiros

### Leituras prioritárias

O quadro é uma seleção inicial, não uma revisão sistemática concluída. Resultados publicados são relatos dos autores, ainda não reproduzidos neste projeto. Para trabalhos acessados parcialmente, localizar o texto completo antes de julgar o método. Status, revisões e erratas devem ser confirmados na fonte editorial.

| ID | Referência e link | O que examinar e solicitar |
|---|---|---|
| R1 | Zeng, Bashir e Nait-Abdesselam. **UAVIDS-2025**, IEEE CNS 2025. [DOI](https://doi.org/10.1109/CNS66487.2025.11194990), [texto disponibilizado pelo autor](https://www.researchgate.net/publication/396599699_UAVIDS-2025_A_Benchmark_Dataset_for_Intrusion_Detection_in_UAV_Networks_Using_Machine_Learning_Techniques) | Tabela IV, atributos, split, extração e simulações. Solicitar código NS-3, extrator, IDs de execução, timestamps, splits e licença do código. O benchmark já inclui árvores e redes profundas. |
| R2 | Zeng, Fu e Nait-Abdesselam. **FedGraph-ID**, IEEE INFOCOM 2026. [DOI](https://doi.org/10.1109/INFOCOM59046.2026.11571676), [texto disponibilizado pelo autor](https://www.researchgate.net/publication/408225701_FedGraph-ID_A_Federated_Graph_Learning_Framework_for_Intrusion_Detection_in_UAV_Networks_Under_Adversarial_Settings) | Construção temporal dos grafos e agregação HYDRA. Solicitar origem dos timestamps, janelas, rótulo de nó/aresta/grafo, particionamento de clientes, código e protocolo de ataques. O CSV local não fornece sozinho todos esses elementos. |
| R3 | Zarkadis e Douligeris. **XAI and Statistical Analysis for Reliable Intrusion Detection in the UAVIDS-2025 Dataset**, preprint de 2026. [Registro](https://arxiv.org/abs/2605.13922), [texto](https://arxiv.org/html/2605.13922v1) | Ensembles, redes tabulares, seleção, calibração e análise Blackhole/Wormhole. Solicitar implementação, definição de duplicata, splits e ordem exata do ajuste das transformações. Conferir versão e eventual publicação posterior. |
| R4 | **Residual-aware lightweight deep learning framework for high-fidelity intrusion detection in UAV swarm networks**, Scientific Reports, 2026. [Artigo](https://www.nature.com/articles/s41598-026-52524-5) | Contraponto central: relata CNN residual com F1-macro 0,9971, 474.629 parâmetros, 1,81 MB e aproximadamente 2,3 ms/amostra. Solicitar código, lista final de atributos, construção dos tensores, splits, hardware, batch e script de medição. Conferir o que foi medido em hardware, o que pertence apenas ao forward e o que é projeção de aplicabilidade. |
| R5 | **Securing UAV Swarms with Vision Transformers: A Byzantine-Robust Federated Learning Framework for Cross-Modal Intrusion Detection**, Drones, 2026. [Artigo](https://www.mdpi.com/2504-446X/10/2/125) | Transformação dos dados, clientes, modalidades e ataques a atualizações. Solicitar código e alinhamento entre modalidades. Usar como contexto; não transplantar métricas para uma tarefa centralizada diferente. |
| R6 | **HADAR-UAV: Risk-Calibrated One-Class Learning Framework for Zero-Day Intrusion Detection in Unmanned Aerial Vehicle Networks**, 2026. [Artigo](https://www.techscience.com/cmc/v89n1/68370/html), [DOI](https://doi.org/10.32604/cmc.2026.080874) | Exclusão de famílias e calibração. Solicitar como foram obtidas as sessões, como ataques entram na seleção e como os splits são reproduzidos. É uma extensão de tarefa, não baseline multiclasse diretamente comparável. |
| R7 | **Advanced explainable ensemble models for multi-class intrusion detection in heterogeneous drone and industrial networks**, 2026. [Artigo](https://link.springer.com/article/10.1186/s13635-026-00234-w) | Contraponto central: relata RF com F1-macro 0,99964, 0,99844 e 0,99994 em Drone IDS, UAVIDS-2025 e ICSCASD-MPLC. Reproduzir criticamente. A Fig. 1 indica remoção de identificadores, mas os resultados apresentam `FlowID` como atributo mais importante do UAVIDS-2025; esclarecer com autores/código se o identificador entrou no treino. Extrair splits, unidade da latência por batch, scripts e dados antes de interpretar os escores. |
| R8 | Artefato **uavsybildetection**. [README do repositório](https://github.com/fagumus/uavsybildetection/blob/main/README.md) | Auditoria de identidade e controles com origens separadas. Confirmar artigo associado, status, commit e licença. A existência do repositório não certifica revisão por pares. |

### Como os três contrapontos entram na contextualização

Não copiar as formulações abaixo literalmente para o artigo final antes de concluir a reprodução. Elas registram a lógica argumentativa e devem ser reescritas com os resultados efetivamente obtidos.

1. **Contra a dicotomia “árvores leves versus redes pesadas”.** R4 relata que uma CNN residual pode atingir alta qualidade com tamanho e tempo de inferência reduzidos. Em contrapartida a essa conclusão de viabilidade, o presente estudo submete redes compactas e ensembles tabulares à mesma informação, aos mesmos protocolos de generalização e à mesma definição de custo ponta a ponta.
2. **Contra a inferência de generalidade a partir de resultados quase perfeitos.** R7 relata RF como melhor modelo em três datasets distintos. O presente estudo distingue consistência do algoritmo entre datasets, transferência entre domínios e possível dependência de identificadores. Essa distinção é necessária porque o artigo apresenta `FlowID` como principal atributo do UAVIDS-2025, apesar de o fluxograma metodológico indicar remoção de identificadores.
3. **Contra o tratamento de cada fluxo como observação independente.** R2 argumenta que ataques coordenados exigem contexto topológico e temporal. O presente estudo testa se o ganho permanece quando modelos tabulares recebem agregados do mesmo contexto e quando a divisão impede compartilhamento de sessões/janelas.

Formulação metodológica segura:

> Em contrapartida a trabalhos que relatam alta qualidade com redes profundas compactas, árvores quase perfeitas em múltiplos datasets ou vantagem de representações em grafos, esta pesquisa não assume a superioridade prévia de nenhuma família. As hipóteses são avaliadas sob informação equivalente, protocolos de generalização explícitos e fronteiras comuns de medição computacional.

Evitar expressões como “ao contrário de R4, deep learning é pesado”, “R7 provou generalização entre datasets” ou “R2 provou que GNN é necessária”. Elas excedem o que as comparações descritas demonstram.

### Busca e matriz de evidências

- [ ] [MANUAL] Buscar o nome exato `UAVIDS-2025` em fontes acadêmicas, registros DOI e repositórios de autores.
- [ ] [MANUAL] Examinar referências e trabalhos que citam R1–R4, incluindo resultados contrários à hipótese do projeto.
- [ ] [MANUAL] Registrar consulta, fonte, data, resultados elegíveis e motivos de exclusão.
- [ ] [MANUAL] Distinguir publicação revisada, preprint, notebook e repositório sem publicação identificada.
- [ ] [MANUAL] Ler métodos, tabelas e disponibilidade de dados/código; não extrair apenas o maior F1 do resumo.
- [ ] [MANUAL] Para cada crítica, anotar seção/tabela e trecho curto ou descrição precisa que a sustenta. Distinguir falha verificada de informação ausente.
- [ ] [MANUAL] Atualizar a busca antes da submissão.

Criar `literature/evidence.csv` com: `reference_id`, título, autores, ano, DOI/URL, versão, status, tarefa, classes, unidade predita, dataset/checksum, atributos, contexto disponível, split, grupos, duplicatas, transformações antes/depois do split, tuning, métricas e averaging, tamanho do teste, hardware, batch, definição de latência, código/commit, licença, limitações verificadas, informações pendentes e data de acesso.

### Recuperar autoria dos notebooks Kaggle

- [ ] [MANUAL] Localizar a página original de `lastversionuav.ipynb` e de `minor-project.ipynb` no histórico de downloads/Kaggle. Os nomes locais não identificam com segurança autor, URL ou versão.
- [ ] [MANUAL] Registrar usuário, título, URL, versão, data, licença e eventual artigo associado.
- [ ] [MANUAL] Não atribuir um notebook a R1 ou R2 apenas porque utiliza o mesmo dataset.
- [ ] [MANUAL] Se a origem não for recuperável, registrar “origem não confirmada”; não usá-lo como implementação oficial de artigo.

### Reutilização de código

- [ ] [MANUAL] Conferir licença e condições de redistribuição de cada implementação. Na ausência de autorização clara, solicitar esclarecimento antes de copiar/redistribuir código; citação não substitui licença.
- [ ] [CÓDIGO] Preservar um snapshot identificado por commit/checksum e suas instruções, sem executar automaticamente células de instalação ou scripts desconhecidos.
- [ ] [CÓDIGO] Criar um adaptador para o protocolo novo, mantendo o original identificável.
- [ ] [REVISÃO] Classificar cada baseline: “reprodução do código original”, “reimplementação do artigo” ou “adaptação sob protocolo comum”.
- [ ] [CÓDIGO] Registrar alterações, parâmetros não informados, correções e efeito de cada mudança em `provenance/third_party_code.csv`.
- [ ] [REVISÃO] Separar a tentativa de reproduzir o resultado original da avaliação corrigida/comum. Não atribuir a versão modificada integralmente ao autor original.

**Critério de conclusão F1:** cada baseline selecionado tem uma referência rastreável, plano de implementação e pendências explícitas. Não é necessário reproduzir todos os trabalhos da tabela.

## 4. F2 — Obtenção de dados e contatos manuais

### Fontes do UAVIDS-2025

- [Dataset no IEEE DataPort — DOI](https://doi.org/10.21227/j5p4-zt27).
- [Depósito no Zenodo](https://zenodo.org/records/15336998).
- [Dataset no Kaggle](https://www.kaggle.com/datasets/qinglizeng1997/uavids-2025).

O depósito Zenodo descreve 122.171 fluxos e 22 atributos, além do rótulo, produzidos por simulação. Usar essa descrição como expectativa de auditoria, não como substituta da inspeção do arquivo efetivamente baixado.

- [ ] [MANUAL] Escolher uma fonte primária e registrar a versão e a licença exibidas nela.
- [x] [CÓDIGO] Registrar a cópia bruta local; calcular SHA-256, tamanho em bytes, linhas, colunas e tipos. Evidência: `research_artifacts/data_audit/data_manifest.json`; correspondência exata com o arquivo registrado como Zenodo v1.
- [ ] [CÓDIGO] Comparar com outras distribuições se forem usadas pelos baselines; diferença de checksum exige investigação de conteúdo e ordenação.
- [ ] [MANUAL] Registrar se o CSV foi arredondado, concatenado, embaralhado ou normalizado antes da publicação.
- [ ] [MANUAL] Obter os PDFs completos de R1–R4 e materiais suplementares disponíveis.

### Solicitação aos autores de R1/R2

Usar os contatos do PDF ou da página institucional atual dos autores. Não há endereço de e-mail verificado neste checklist. O envio deve ser feito pelo pesquisador; este plano não envia mensagens.

- [ ] [MANUAL] Solicitar scripts NS-3 e versão exata, alterações locais, configurações, sementes e extrator de atributos.
- [ ] [MANUAL] Solicitar `simulation_id`, `scenario_id`, seed, número de UAVs, mobilidade, intensidade/instante dos ataques e associação de cada linha ao cenário.
- [ ] [MANUAL] Solicitar timestamps de início/fim, identificador de sessão e mapeamento entre IP e dispositivo dentro de cada execução.
- [ ] [MANUAL] Perguntar se `FlowID` tem significado temporal ou apenas identificador, e se reinicia entre execuções.
- [ ] [MANUAL] Perguntar pelas fórmulas exatas de `PacketDropRate`, `AverageHopCount`, taxas, duração e contabilização de pacotes perdidos.
- [ ] [MANUAL] Solicitar explicação dos registros equivalentes e dos valores de `PacketDropRate > 1`, sem pressupor erro ou assinatura de ataque.
- [ ] [MANUAL] Solicitar PCAP/XML/saídas FlowMonitor, quando disponíveis, e licença/permissão de redistribuição.
- [ ] [MANUAL] Para R2, solicitar qual versão dos dados suporta a construção temporal dos grafos.

### Modelo de mensagem para envio manual

> Subject: Reproducibility materials for UAVIDS-2025 research
>
> Dear authors,
>
> I am developing a reproducible study of generalization and local-versus-edge inference using UAVIDS-2025, and will cite your work. Could you share the available simulation scripts, feature extraction code, original train/test indices and dataset version used in your experiments?
>
> To avoid overlap across evaluation partitions, I would also like to clarify whether flow records can be linked to simulation runs, sessions, device identities and timestamps. In particular, is FlowID chronological, and are the formulas for PacketDropRate and AverageHopCount available?
>
> If any materials cannot be shared, a clarification of these points would still be very helpful. Please also indicate the applicable code/data license and whether redistribution of derived split manifests is permitted.
>
> Thank you,
> [name, affiliation, project link]

Adaptar aos métodos específicos de R3–R8, solicitando código, splits, parâmetros e scripts de medição. Registrar data de envio, resposta, anexos e questões não resolvidas em `literature/contact_log.md`.

### Decisão se não houver materiais adicionais

| Material disponível | Caminho permitido | Limite a declarar |
|---|---|---|
| Apenas CSV | Modelos tabulares, grupos por assinatura, origens e benchmark de requisições | Sem cronologia validada, sem generalização por sessão real e sem tempo desde início do ataque |
| CSV + IDs de execução | Separar execuções completas | Ainda verificar se atributos estão disponíveis causalmente |
| CSV + timestamps + sessões | Contexto causal e avaliação temporal | Não compartilhar registros de janelas entre partições; definir intervalo de exclusão |
| Scripts + extração reproduzível | Gerar cenários independentes | Novas execuções continuam sendo simulação, não validação em voo |
| Hardware embarcado | Medição física no equipamento | Restringir conclusão à placa, configuração e carga medidas |

**Critério de conclusão F2:** fonte congelada e decisão documentada sobre qual linha dessa tabela será seguida. A ausência de materiais bloqueia apenas os experimentos dependentes deles.

## 5. F3 — Auditoria e contrato dos dados

- [x] [CÓDIGO] Criar `data_manifest.json` e `data_dictionary.csv`: nome, tipo, unidade, definição, fórmula, domínio, fonte e disponibilidade temporal de cada atributo. Definições não confirmadas permanecem marcadas como provisórias.
- [x] [CÓDIGO] Contar classes, ausentes, infinitos, constantes e anomalias verificáveis sem inventar domínios físicos ainda não confirmados.
- [x] [CÓDIGO] Contar duplicatas considerando: linha completa; atributos sem identificadores; atributos mais rótulo; assinatura numérica sem rótulo.
- [x] [CÓDIGO] Para assinaturas iguais com classes diferentes, quantificar conflitos; não escolher rótulo majoritário global nem apagá-los silenciosamente.
- [x] [CÓDIGO] Medir classes e frequência por IP, portas, ordem das linhas e faixas de FlowID. Tratar conclusões como diagnóstico do dataset, não teste final de hipótese de modelo.
- [x] [CÓDIGO] Investigar relações algébricas e redundâncias com tolerâncias e unidades registradas.
- [x] [CÓDIGO] Comparar especificamente `LostPackets / TxPackets` e `PacketDropRate`, sem afirmar que uma derivada cria informação independente.
- [x] [CÓDIGO] Distinguir ausência de contexto de ausência de valor; nenhuma estatística global deve substituir contexto não observado.
- [x] [REVISÃO] Separar auditoria de integridade do estudo supervisionado de atributos. EDA que orientar seleção deverá usar apenas os dados de desenvolvimento.
- [x] [MANUAL] Registrar a exposição anterior ao dataset completo. Recomeçar o código não transforma esse dataset em uma avaliação historicamente intocada.

### Política de atributos inicial

- `FlowID`: usar para rastreabilidade e controles diagnósticos; excluir dos modelos principais.
- `Protocol`: excluir se a constância for confirmada.
- `SrcAddr`/`DstAddr`: manter como metadados para grupos; excluir do painel principal sem identidade. Avaliar sua inclusão apenas em ablação identificada.
- Portas: decidir representação numérica/categórica no desenvolvimento e incluir custo de codificação.
- Derivadas: especificar fórmula, unidade e tratamento de denominador zero. Não chamar `Throughput/(AverageHopCount+1)` de divisão exata pelo número de saltos.
- Corte de valores: preservar versão bruta e comparar política predefinida de manter/tratar. Não editar valores para melhorar o teste.

Uma medição local em drone também precisa considerar se o drone consegue observar todos os atributos. Estatísticas de envio e recebimento calculadas globalmente pelo simulador podem não estar disponíveis em um único nó. Se isso não puder ser estabelecido, descrever a inferência sobre vetores prontos, sem alegar um IDS embarcado plenamente implementado.

**Entregáveis:** `reports/data_audit.md`, dicionário, manifesto e política de limpeza. **Critério de conclusão:** nenhuma transformação depende de uma explicação não confirmada apresentada como fato.

## 6. F4 — Protocolo experimental congelado

### Protocolos de particionamento

| ID | Regra | Interpretação |
|---|---|---|
| S0 | Divisão aleatória estratificada por rótulo | Referência de interpolação em distribuição semelhante |
| S1 | Agrupar assinaturas dos atributos numéricos originais sem identificadores e sem rótulo | Sensibilidade à repetição exata de padrões |
| S2 | Origens de treino e teste separadas | Transferência para endereços de origem não vistos |
| S3 | Execuções/cenários completos separados, se houver metadados | Transferência entre simulações |

- [x] [CÓDIGO] Definir assinatura S1 sobre o conjunto fixo de atributos antes de comparar modelos/ablações. A implementação usa fatoração da tupla exata, sem arredondamento ou dependência de colisão de hash.
- [x] [CÓDIGO] Em S1, registros equivalentes com rótulos diferentes continuam no mesmo grupo.
- [x] [CÓDIGO] Usar todas as linhas em S1, preservando frequência. Avaliação com um representante por assinatura é uma análise secundária de população diferente.
- [x] [CÓDIGO] Em S2, medir sobreposição de destinos e de assinaturas. Uma origem nova não implica um dispositivo ou padrão novo.
- [ ] [MANUAL] Se IPs forem reutilizados entre simulações, usar identificador composto quando possível; não inventar correspondência global entre IP e UAV.
- [x] [CÓDIGO] Não prometer eliminação simultânea de todas as sobreposições em S1/S2. Um protocolo combinado exige agrupar componentes conectados pelas restrições e verificar se sobram grupos/classes suficientes.
- [x] [CÓDIGO] Inspecionar número e tamanho dos grupos e cobertura por classe. Se a estratificação perfeita for impossível, preservar grupos e reportar proporções reais.
- [x] [CÓDIGO] Se uma classe faltar no treino/teste, registrar a limitação; não eliminar a classe da média silenciosamente. O gerador falha se um fold candidato perder uma classe.
- [x] [CÓDIGO] Salvar índices e IDs de grupo de cada divisão. Não regenerar splits separadamente para cada modelo.

S1 e S2 não reconstroem sessões. S3 é preferível para afirmações sobre novos cenários quando os metadados forem confiáveis. A documentação de [validação por grupos](https://scikit-learn.org/stable/modules/cross_validation.html) descreve os divisores disponíveis; a escolha do grupo é responsabilidade do estudo.

### Desenvolvimento, seleção e avaliação

Plano inicial recomendado, sujeito à viabilidade dos grupos:

1. Reservar uma parcela de desenvolvimento para depurar código e escolher o protocolo; seus resultados não entram como confirmação final.
2. Para avaliação comparativa, usar CV externa de cinco folds no restante, com grupos em S1/S2/S3 e estratificação em S0. Se os grupos não permitirem cinco folds, definir e justificar outro número antes da execução final.
3. Usar CV interna de três folds, sob a mesma restrição de grupos, para tuning. A função de busca recebe somente o treino externo.
4. Repetir inicialmente três sementes de ajuste para modelos estocásticos; um piloto determina se são necessárias mais para estabilizar as estimativas. Não interpretar sementes como novos datasets independentes.
5. Separar seleção/calibração de política operacional dentro do desenvolvimento, sem usar predições do teste externo para ajustar limiares.
6. Se houver novas simulações, congelar decisões antes de avaliá-las como confirmação externa. Essa etapa é mais forte do que redistribuir novamente as mesmas linhas.

- [x] [MANUAL] Congelar orçamento exploratório de tuning por família e registrar o custo real. Evidência: `configs/nested_tuning_v2.json` e `reports/nested_tuning_v2/`; o orçamento confirmatório permanece pendente.
- [x] [MANUAL] Congelar espaços exploratórios, regra de desempate, métrica e comportamento em falhas para v2.
- [x] [CÓDIGO] Registrar número real de fits, convergência, duração e tentativas inválidas. Evidência inicial: 105/105 jobs em `results/predictive_baseline_v1/`; a MLP registrou não convergência no limite escolhido.
- [ ] [CÓDIGO] Early stopping acessa somente partição interna, nunca o teste externo.
- [x] [REVISÃO] Não escolher novo modelo, atributo ou hiperparâmetro após consultar resultados externos e continuar chamando a avaliação de confirmatória. A versão v1 foi registrada explicitamente como exploratória; alterações exigem nova versão.

Referências de implementação: [vazamento e pipelines](https://scikit-learn.org/stable/common_pitfalls.html) e [CV aninhada](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html). Elas orientam o mecanismo; não garantem independência dos dados sem grupos adequados.

**Entregáveis:** `protocol/evaluation_v1.md`, `configs/`, `splits/`, `protocol/deviations.md`. **Critério de conclusão:** um terceiro consegue identificar exatamente quais dados cada etapa pode acessar.

## 7. F5 — Implementação nova e verificações

### Organização sugerida

```text
uavids-study/
  README.md
  pyproject.toml
  <arquivo de dependências travadas>
  protocol/           # escopo, hipóteses, métricas e desvios
  literature/         # evidências, bibliografia e contatos
  provenance/         # terceiros, uso de IA e alterações
  configs/            # dados, splits, modelos e cenários
  data/raw/           # cópias brutas conforme licença
  data/processed/     # derivados reconstruíveis
  splits/             # índices/IDs estáveis
  src/uavids_study/   # auditoria, features, splits, treino e avaliação
  experiments/        # comandos de execução em lote
  tests/              # invariantes metodológicas e casos pequenos
  benchmarks/         # cliente, servidor, rede e coleta de métricas
  results/            # métricas, predições e medições brutas
  reports/            # tabelas/figuras geradas e diagnóstico
  paper/              # texto, bibliografia e figuras finais
```

Essa árvore é uma especificação futura; criar este MD não cria ou implementa esses componentes.

- [ ] [CÓDIGO] Criar ambiente isolado novo e dependências compatíveis travadas; não herdar automaticamente requisitos antigos.
- [x] [CÓDIGO] Configurar sementes, threads e dispositivos explicitamente; salvar versões, SO e informações de CPU/acelerador. O commit deverá ser acrescentado quando esta linha de trabalho for versionada.
- [x] [CÓDIGO] Implementar módulos reutilizáveis; notebooks serão interfaces de exploração e apresentação, não fonte exclusiva de execução. A auditoria está em `src/uavids_study/data_audit.py`.
- [ ] [CÓDIGO] Implementar comandos equivalentes a `audit`, `make-splits`, `train`, `evaluate`, `benchmark` e `make-report`.
- [x] [CÓDIGO] Salvar predições, probabilidades e ordem explícita das classes por exemplo avaliado.
- [x] [CÓDIGO] Congelar schemas e incluir checksum de dados, split e configuração em cada execução.
- [x] [CÓDIGO] Impedir que o estimador receba rótulos de teste ou metadados proibidos; a função de métricas avalia as predições após a inferência.
- [x] [CÓDIGO] Registrar falhas sem substituí-las por zeros nem descartar silenciosamente execuções ruins.

### Baselines do núcleo

| Modelo | Papel | Controle necessário |
|---|---|---|
| Dummy/majoritário | Sanidade | Métrica e distribuição de referência |
| Regressão logística | Baseline linear | Escalonamento no treino e convergência |
| Random Forest | Baseline forte de árvores | Faixa de capacidade suficiente; medir tamanho e custo |
| XGBoost ou LightGBM | Boosting | Escolher biblioteca no desenvolvimento ou incluir ambas explicitamente |
| Stacking | Integração de modelos | Predições fora da amostra e custo completo |
| MLP compacta | Baseline neural tabular | Mesmos atributos, tuning, seeds e early stopping correto |

Escolher uma composição de stacking executável e registrada, por exemplo RF + boosting + MLP com meta-modelo linear. Se for escolhida RF + XGBoost + LightGBM para aproveitar a ideia anterior, ambas as bibliotecas passam a integrar o plano e o orçamento. Não alterar composição porque o teste favoreceu outra.

### Stacking sem contaminação interna

- [ ] [CÓDIGO] Cada estimador base deve conter seu próprio pré-processamento aprendido nos dados permitidos.
- [ ] [CÓDIGO] Gerar probabilidades OOF: cada exemplo usado para treinar o meta-modelo deve ser predito por bases que não o usaram no ajuste.
- [ ] [CÓDIGO] Usar folds internos compatíveis com os grupos do treino corrente; índices devem ser relativos a esse subconjunto.
- [ ] [CÓDIGO] Não usar `cv=5` como prova de tratamento de grupos. Verificar a API da versão instalada e passar splits explícitos ou implementar OOF controlado.
- [ ] [CÓDIGO] Não reutilizar em um fold modelos ajustados em partições mais amplas; incluir seleção das bases no fluxo de treinamento interno definido.
- [ ] [REVISÃO] Conferir com conjuntos pequenos que nenhuma assinatura/grupo proibido cruza o ajuste OOF.

Consultar a semântica de [StackingClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.StackingClassifier.html), especialmente a finalidade das predições de validação cruzada para o meta-modelo.

### Testes que protegem a validade científica

- [x] Testar ausência de interseção de IDs entre treino e teste nos folds candidatos S0/S1/S2.
- [x] Testar ausência de grupos compartilhados conforme S1/S2; S3 segue indisponível sem identificador de execução.
- [x] Testar que estatísticas de transformação ignoram valores extremos inseridos apenas no teste.
- [x] Testar ordem das classes: suportes, matriz de confusão, probabilidades e relatório devem concordar.
- [x] Testar métricas com uma matriz pequena calculada manualmente, incluindo classe sem predição.
- [x] Testar contagem de registros e unicidade das predições OOF.
- [ ] Testar fórmulas de atributos, denominadores zero, infinitos e unidades.
- [ ] Testar reexecução determinística dentro das tolerâncias definidas para o ambiente.
- [ ] Rodar controle com rótulos aleatorizados coerentemente com a unidade de independência; resultado anormalmente alto exige investigação, não uma conclusão automática de fraude/vazamento.
- [x] Executar teste ponta a ponta pequeno antes do benchmark completo, incluindo exportação e recálculo de métricas.

**Critério de conclusão F5:** o fluxo completo funciona fora de notebooks, com testes das invariantes e trilha de acesso aos dados.

## 8. F6 — Experimentos preditivos e ablações

### Painel principal

- [x] Executar baselines no conjunto de atributos principal sem identidade, em S0/S1 e em S2 quando viável. Evidência exploratória: `results/predictive_baseline_v1/`.
- [ ] Incluir S3 se metadados permitirem; dar a ele destaque proporcional à qualidade da identificação de cenários.
- [x] Reportar todos os modelos planejados para o baseline v1, não só o vencedor.
- [x] Comparar custo do ajuste e inferência, além de qualidade; os tempos desta rodada permanecem diagnósticos e não substituem F7.
- [x] Não atribuir a diferença entre S0 e S1 exclusivamente a vazamento: há também diferença de distribuição, tamanho e dificuldade dos testes.
- [ ] Produzir diagnóstico complementar de desempenho em linhas vistas/equivalentes e inéditas dentro do teste S0, sem treinar após observar o diagnóstico.

### Desenho dos três experimentos centrais

| Experimento | Pergunta principal | Tratamentos mínimos | Controle decisivo | Resultado que refuta a hipótese do projeto |
|---|---|---|---|---|
| E1 — Compacto | Redes compactas dominam árvores? | RF, Extra Trees, boosting, MLP e CNN residual | Mesmos atributos, splits, tuning comparável, batch e hardware | Rede não supera melhor árvore na fronteira qualidade–custo, ou vice-versa |
| E2 — Multi-dataset | RF é consistentemente suficiente? | Reprodução fiel e corrigida em UAVIDS-2025, Drone IDS e ICSCASD-MPLC | Remoção de IDs, transformações dentro dos folds e splits coerentes com cada dataset | Quase perfeição permanece mesmo sob controles rigorosos |
| E3 — Contexto | Relações/janelas acrescentam informação? | Fluxo isolado, agregados tabulares de contexto e modelo relacional/temporal | Mesmo contexto observável e divisão anterior à construção | Agregados tabulares igualam GNN/temporal ou contexto não melhora o teste |

- [ ] [MANUAL] Obter e licenciar Drone IDS e ICSCASD-MPLC a partir das referências primárias de R7; não usar um espelho sem conferir versão/checksum.
- [ ] [MANUAL] Confirmar número de classes, unidade amostral, origem dos rótulos, sessões e atributos de cada dataset antes de escrever o comparativo.
- [ ] [CÓDIGO] Em E2, manter um protocolo próprio por dataset quando a estrutura exigir. “O mesmo protocolo” significa os mesmos princípios contra contaminação, não forçar o mesmo divisor a dados incompatíveis.
- [x] [CÓDIGO] Produzir dois resultados diagnósticos inspirados em R7 no UAVIDS-2025: com `FlowID` e sem `FlowID`, sem chamar a execução de reprodução fiel sem o código original.
- [x] [CÓDIGO] Não usar desempenho com `FlowID` para selecionar features ou ajustar o painel principal.
- [ ] [MANUAL] Tratar a aparente inconsistência de R7 como questão de reprodutibilidade até examinar código ou obter resposta dos autores; não alegar erro metodológico como fato consumado.
- [ ] [CÓDIGO] Em E3, registrar quantos fluxos e quanto tempo de observação são necessários antes de cada decisão; comparar também o atraso introduzido pela janela.

### Ablações planejadas

| ID | Comparação | Fatores a manter constantes |
|---|---|---|
| A1 | Originais × originais + três derivadas × remoção individual de cada derivada | Split, orçamento e definição do pipeline |
| A2 | RF com capacidade limitada × faixa mais ampla de capacidade | Dados, métrica e orçamento registrado |
| A3 | Melhor base × stacking | Tarefa, dados disponíveis e protocolo |
| A4 | Sem IPs × codificação de IPs aprendida no treino | Grupos e tratamento de valores desconhecidos |
| A5 | Cinco classes × quatro classes treinadas × previsões de cinco agrupadas | Mesmos exemplos e métrica na mesma taxonomia ao comparar |
| A6 | Manter × tratar valores anômalos conforme política | Não mudar simultaneamente outras features |
| A7 | Com `FlowID` × sem `FlowID` | Reprodução diagnóstica de R7; resultado principal sempre sem identificador |
| A8 | Fluxo isolado × agregados de contexto × modelo relacional/temporal | Mesmas observações causais, grupos e horizonte de decisão |

- [ ] Definir se A1/A6 medem contribuição com hiperparâmetros fixos ou ganho com retuning. Se ambos, apresentar separadamente.
- [ ] Em A5, calcular métricas de quatro classes para as duas estratégias comparadas; não comparar diretamente o F1-macro de cinco com o de quatro.
- [ ] Para agrupamento probabilístico, somar probabilidades das classes originais antes de decidir; distinguir isso de mapear a classe vencedora após argmax.
- [ ] Não usar importância Gini/SHAP como substituta de ablação causal do componente.
- [ ] Explicar Blackhole/Wormhole com erros e atributos de desenvolvimento; figuras do teste são análise pós-avaliação, sem reajuste posterior do método.

### Métricas preditivas

- [x] Primária: F1-macro nas cinco classes fixas, com ordem e tratamento de classes sem predição congelados.
- [x] Secundárias: precision/recall/F1 por classe, accuracy, balanced accuracy e matriz de confusão absoluta e normalizada por classe verdadeira.
- [x] Falsos alarmes: fluxos normais classificados como qualquer ataque / total de fluxos normais.
- [x] Ataques perdidos: fluxos de ataque classificados como normais / total de fluxos de ataque; distinguir de erro entre tipos de ataque.
- [ ] Se avaliar binário, declarar qual é a classe positiva e reportar F1 dessa classe separadamente de F1-macro.
- [ ] Se usar probabilidades, incluir log loss e uma avaliação de calibração com definição explícita. A calibração usa apenas treino/validação apropriados.
- [ ] Se variar prevalência para representar operação, manter isso como análise secundária, com proporções justificadas e sem retuning no teste.

**Entregáveis:** predições por fold/seed, métricas brutas, tabelas e resultados de ablações. **Critério de conclusão:** diferenças podem ser recalculadas sem carregar ou retreinar os modelos.

## 9. F7 — Benchmark de inferência local e na borda

### Definir o que é medido

| Medida | Início → fim | Condição |
|---|---|---|
| Tempo do modelo | Entrada pronta do estimador → saída | Exclui extração e comunicação |
| Tempo do pipeline | Vetor bruto disponível → predição | Inclui derivadas, codificação e pré-processamento |
| Latência da requisição | Envio pelo cliente → resposta recebida | Inclui serialização, rede, fila e pipeline |
| Tempo até detectar ataque | Início verificável do ataque → alerta | Exige tráfego temporal, extração causal e evento conhecido |

Reproduzir linhas do CSV em uma agenda artificial mede atendimento de vetores de fluxo. Não reproduz a cronologia original nem o efeito de perda/jitter sobre os atributos que originaram o CSV.

- [ ] [MANUAL] Definir se o cenário é um UAV com inferência própria, um cliente representativo ou um coletor central. Especificar o acesso aos atributos.
- [ ] [MANUAL] Definir transporte, formato, tamanho do payload, conexões persistentes, TLS se aplicável e política de timeout/retry.
- [ ] [MANUAL] Fixar critério operacional de prazo com fonte/justificativa. Na ausência de requisito real, usar análise de sensibilidade, sem chamar valores arbitrários de SLA de voo.
- [x] [CÓDIGO] Selecionar candidatos pelo desenvolvimento, ajustar artefatos para benchmark em todos os dados depois da avaliação e congelar hashes antes da medição. Esses artefatos não produzem métricas preditivas de treino.
- [x] [CÓDIGO] Congelar os mesmos artefatos a serem usados nas posições local e borda, para isolar localização. A posição em container ainda está pendente.
- [ ] [CÓDIGO] Depois comparar configurações com modelos de tamanhos diferentes, explicitando a mudança de dois fatores.

### Bancada e controles

- [ ] [MANUAL] Preferir host Linux dedicado ou registrar detalhadamente VM/WSL2 e Docker Desktop. Não equiparar vCPU limitada a processador ARM específico.
- [ ] [CÓDIGO] Separar processos/containers do gerador, inferência e coleta. Evitar que o gerador seja o gargalo ou concorra nos mesmos núcleos sem medição.
- [ ] [CÓDIGO] Aplicar limites CPU/RAM, fixar threads e registrar throttling, OOM e uso de swap.
- [ ] [CÓDIGO] Medir baseline sem restrições e baseline sem degradação de rede.
- [ ] [CÓDIGO] Aplicar netem apenas às interfaces da bancada; registrar direção, atraso de cada sentido, distribuição e semente quando suportada.
- [ ] [CÓDIGO] Verificar RTT, perda observada e banda efetiva antes de cada perfil. Configuração nominal não basta.
- [ ] [CÓDIGO] Em TCP, registrar retries/timeouts: perda de pacote pode produzir retransmissão e aumento de latência, não necessariamente perda de requisição.
- [ ] [CÓDIGO] Não alterar o tráfego de administração ou a rede pessoal durante os testes.

Documentação: [recursos do Docker](https://docs.docker.com/engine/containers/resource_constraints/) e [netem](https://man7.org/linux/man-pages/man8/tc-netem.8.html). São mecanismos de limitação/emulação; não reproduzem automaticamente rádio, mobilidade ou consumo energético de drones.

### Matriz inicial para o piloto — não são condições reais comprovadas

| Fator | Níveis iniciais sugeridos |
|---|---|
| CPU | 0,5; 1; 2 CPUs equivalentes em quota, sempre com host identificado |
| RAM | 512 MiB; 1 GiB; 2 GiB; registrar configurações inviáveis |
| Atraso adicional | 0; 10; 50; 100 ms por sentido explicitamente configurado |
| Jitter/perda | Baseline e perfis independentes; exemplos de perda: 0%; 0,1%; 1% |
| Banda | Baseline sem limite adicional; 1; 10; 100 Mbit/s |
| Batch | 1 como principal; lotes adicionais como experimento separado |
| Carga | Escalonar taxa oferecida até antes, perto e além da saturação |

Não executar automaticamente o produto cartesiano de tudo. Primeiro variar um fator, identificar faixas críticas e congelar uma matriz reduzida com interações justificadas. Valores plausíveis para aplicação UAV precisam de fonte ou nova simulação; caso contrário, chamá-los de análise de sensibilidade.

### Medição rigorosa

- [ ] [CÓDIGO] Usar relógio monotônico de alta resolução e IDs de requisição. Medir ida/volta no mesmo cliente; latência de um sentido exige relógios sincronizados e erro conhecido.
- [x] [CÓDIGO] Separar carregamento, aquecimento e regime estável no piloto local.
- [x] [CÓDIGO] Medir chamada individual e lotes separadamente. O custo dividido pelo lote foi rotulado como amortizado.
- [ ] [CÓDIGO] Se houver GPU, sincronizar corretamente. Consultar [benchmark PyTorch](https://docs.pytorch.org/tutorials/recipes/recipes/benchmark.html).
- [ ] [CÓDIGO] Usar carga de chegada programada independente das respostas para investigar filas; registrar atraso do próprio gerador em relação ao envio agendado.
- [ ] [CÓDIGO] Registrar requisições agendadas, enviadas, concluídas, falhas, retries e descartes. Reportar latência de sucessos junto com disponibilidade, sem ocultar timeouts.
- [ ] [CÓDIGO] Registrar P50/P95/P99, vazão, CPU, RAM, bytes transmitidos e violações de prazo. O piloto local já cobre percentis, vazão e RSS de carregamento; CPU, bytes e prazo dependem do benchmark cliente–servidor.
- [x] [CÓDIGO] Como piloto local, realizar cinco repetições, 200 chamadas de aquecimento e 5.000 medições individuais por modelo; a bancada cliente–servidor ainda definirá duração por configuração.
- [ ] [CÓDIGO] Aleatorizar a ordem dos modelos/perfis; registrar temperatura e atividade concorrente quando relevantes.
- [x] [CÓDIGO] Preservar medições individuais em formato estruturado; tabelas foram geradas delas.
- [ ] [REVISÃO] Só afirmar consumo de energia se houver medição de potência/energia com equipamento e intervalo definidos. CPU, RAM e FLOPs não são consumo de bateria.

**Critério de conclusão F7:** há evidência de que carga, limites e perfis foram efetivamente aplicados, além de medições reproduzíveis e fronteiras claras do tempo medido.

## 10. F8 — Contexto condicionado por metadados e extensões opcionais

O experimento de contexto E3 é central, mas sua forma temporal ou em grafos depende dos metadados disponíveis. Encaminhamento seletivo, federação e ataques desconhecidos continuam opcionais.

### Encaminhamento seletivo para a borda

- [ ] [MANUAL] Fazer busca específica de novidade em inferência seletiva, offloading e cascatas de IDS antes de propor algoritmo novo.
- [ ] [CÓDIGO] Comparar sempre local, sempre borda, regra fixa e encaminhamento por confiança/rede.
- [ ] [CÓDIGO] Calibrar probabilidades e selecionar limiares apenas em desenvolvimento. [Documentação de calibração](https://scikit-learn.org/stable/modules/calibration.html).
- [ ] [CÓDIGO] Incluir custo do modelo local, calibração, decisão, comunicação e modelo remoto.
- [ ] [CÓDIGO] Definir fallback em timeout e contabilizar casos sem decisão. Não calcular F1 apenas nos casos fáceis atendidos.
- [ ] [CÓDIGO] Reportar cobertura, qualidade entre atendidos, qualidade do sistema completo, taxa de encaminhamento e cumprimento de prazo por classe.

### Contexto temporal ou GNN

- [ ] [MANUAL] Confirmar timestamps/sessões com R1/R2. Sem isso, não chamar janelas de linhas consecutivas de sequência temporal real.
- [ ] [CÓDIGO] Dividir sessões/execuções antes de criar janelas; impedir compartilhamento de registros brutos entre partições, incluindo a janela de observação e horizonte do rótulo.
- [ ] [CÓDIGO] Garantir que a informação de uma predição já estava disponível naquele instante.
- [ ] [CÓDIGO] Definir se o grafo representa comunicação entre IPs ou topologia física; o primeiro não prova o segundo.
- [ ] [CÓDIGO] Definir tarefa de nó, aresta ou grafo e como compará-la à tarefa tabular.
- [ ] [CÓDIGO] Avaliar uma árvore/MLP com estatísticas do mesmo contexto para separar representação de arquitetura.
- [ ] [CÓDIGO] Declarar cenário indutivo ou transdutivo e acesso a nós/arestas não rotulados de teste. Não misturar os dois na conclusão.
- [ ] [CÓDIGO] Incluir coleta e construção do grafo na medição completa, não só forward da rede.

### Aprendizado federado e votação

- [ ] [MANUAL] Adicionar apenas se houver orçamento e pergunta específica; uma publicação posterior pode ser mais adequada.
- [ ] [CÓDIGO] Comparar a mesma MLP centralizada, treinada apenas localmente e federada, com mesma população e orçamento descrito.
- [ ] [CÓDIGO] Dividir teste antes de distribuir treino entre clientes; registrar mapeamento e sobreposição zero entre seus exemplos privados.
- [ ] [CÓDIGO] Distinguir clientes artificiais de UAVs identificados nos dados. Partição não IID artificial não demonstra heterogeneidade física real.
- [ ] [CÓDIGO] Comparar IID e não IID com mecanismos/sementes fixos; não duplicar exemplos entre clientes para fabricar vantagem.
- [ ] [CÓDIGO] Separar agregador de defesa. Se a defesa substituir FedAdam/FedYogi, nomear o algoritmo efetivamente executado.
- [ ] [CÓDIGO] Definir ameaça, capacidade do atacante, fração comprometida, ataques e acesso à informação. Não usar identidade verdadeira dos atacantes na defesa avaliada, exceto como limite ideal explicitamente identificado.
- [ ] [CÓDIGO] Para votação, usar detectores distintos ou justificar correlações. Replicar uma previsão com ruído é controle sintético, não enxame independente.
- [ ] [CÓDIGO] Medir comunicação e duração das rodadas separadamente da inferência.

### Ataques não vistos e novos cenários

- [ ] [CONDICIONAL] Se seguir R6, reservar famílias completas também fora de tuning/calibração conforme a hipótese; declarar precisamente quais ataques orientaram seleção.
- [ ] [CONDICIONAL] Não chamar confiança baixa de prova de detecção zero-day.
- [ ] [CONDICIONAL] Gerar cenários NS-3 independentes apenas com extrator e rótulos validados; preservar seeds e configurações.
- [ ] [CONDICIONAL] Se usar outro dataset, justificar compatibilidade de unidades, tarefas e atributos. Retreinar do zero em outro dataset é replicação, não transferência direta do mesmo modelo.

## 11. F9 — Estatística e interpretação

- [ ] [MANUAL] Fixar contraste principal, por exemplo diferença de F1-macro entre RF e stacking em S1, e contrastes secundários antes da análise final.
- [ ] [MANUAL] Definir diferença mínima de interesse prático no desenvolvimento, incluindo ganho de qualidade e custo aceitável. Não escolhê-la depois de conhecer o resultado.
- [ ] [CÓDIGO] Comparar modelos nos mesmos exemplos/folds e reportar diferenças absolutas, não só porcentagem relativa.
- [ ] [CÓDIGO] Calcular F1 das predições e descrever como folds/seeds são resumidos. Média dos F1 de folds e F1 de predições concatenadas não são idênticos.
- [ ] [CÓDIGO] Para intervalos condicionais a modelos ajustados, considerar bootstrap pareado de grupos de teste completos em S1/S2/S3. Se houver poucos grupos, explicitar a fragilidade do intervalo.
- [ ] [REVISÃO] Bootstrap de predições fixas não captura toda a variabilidade do treinamento. Separar essa incerteza da variação entre ajustes/sementes.
- [ ] [REVISÃO] Não aplicar teste t comum a folds sobrepostos como observações independentes. Não interpretar três seeds como três populações independentes.
- [ ] [MANUAL] Se usar testes de hipótese, justificar unidade independente e aplicar controle de comparações múltiplas aos contrastes planejados. Solicitar revisão estatística se houver dúvida sobre dependências.
- [ ] [CÓDIGO] Para latência, resumir execuções independentes; não tratar milhares de requisições correlacionadas como milhares de repetições independentes da bancada.
- [ ] [CÓDIGO] Produzir fronteira qualidade–latência–memória: um modelo é dominado quando outro é pelo menos tão bom em todos os critérios considerados e melhor em algum, respeitando incerteza.
- [ ] [REVISÃO] Ausência de significância não prova equivalência; equivalência/não inferioridade exigem margem e método definidos previamente.
- [ ] [REVISÃO] Não generalizar vantagem na bancada para voo real, economia de bateria ou todos os ambientes UAV.

### Tabelas e figuras mínimas

- [ ] Literatura e comparabilidade dos protocolos.
- [ ] Auditoria, distribuições, grupos e sobreposições por split.
- [ ] Resultados preditivos por modelo/protocolo, com dispersão e incerteza.
- [ ] Matriz de confusão e erros Blackhole/Wormhole.
- [ ] Ablações e custo de cada componente.
- [ ] Latência versus carga, com erros/timeouts e vazão.
- [ ] Qualidade versus latência/memória sob perfis selecionados.
- [ ] Quadro de ameaças à validade e limitações não resolvidas.

## 12. Uso responsável de IA na programação dos experimentos

IA pode acelerar a implementação, mas não deve definir silenciosamente o método, preencher parâmetros ausentes como se fossem oficiais ou redigir resultados antes das execuções. A responsabilidade científica continua sendo do pesquisador.

### Antes de solicitar código

- [ ] [MANUAL] Fornecer à IA apenas o módulo a implementar, contrato de entrada/saída, protocolo, referências e critérios de aceitação relevantes.
- [ ] [MANUAL] Identificar trechos externos como material de referência, não instruções automáticas de execução.
- [ ] [MANUAL] Distinguir valores confirmados, decisões próprias e dúvidas que devem permanecer pendentes.
- [ ] [MANUAL] Proibir alteração de splits, métricas e orçamento para “melhorar resultado”.
- [ ] [MANUAL] Não solicitar reprodução fiel de método sem fornecer ou confirmar sua especificação.

### Durante e depois da geração

- [ ] [CÓDIGO] Produzir mudanças pequenas, revisáveis e ligadas a itens deste checklist.
- [ ] [REVISÃO] Conferir acesso aos dados, fórmulas, averaging, labels, seeds, threads, folds e caminhos.
- [ ] [REVISÃO] Revisar a semântica das APIs na documentação da versão instalada, especialmente grupos, OOF e calibração.
- [ ] [REVISÃO] Inspecionar se testes verificam propriedades científicas independentes, em vez de repetir a implementação.
- [ ] [CÓDIGO] Executar exemplos pequenos com resposta conhecida, depois integração e só então processamento completo.
- [ ] [CÓDIGO] Registrar em `provenance/ai_assistance.md`: data, ferramenta/modelo quando disponível, tarefa, arquivos afetados, prompt ou resumo, decisões humanas, revisão e testes executados.
- [ ] [REVISÃO] Conferir referências por DOI/página real; não aceitar bibliografia sugerida sem verificação.
- [ ] [REVISÃO] Conferir política vigente da publicação-alvo sobre declaração de uso de IA e autoria antes da submissão.

### Modelo de solicitação à IA

```text
Implemente apenas [módulo] do protocolo [versão], etapa [ID].
Objetivo científico: [pergunta e propriedade a preservar].
Entradas: [schemas, unidades, IDs, grupos e dados permitidos].
Saídas: [schemas, artefatos e identificação da execução].
Restrições: [acesso ao teste, sem alteração dos splits, seeds,
orçamento e comportamento em erros].
Referência: [artigo/seção, documentação e versão/commit].
Não confirmado: [lista; não preencher como fato].
Critérios de aceitação: [invariantes e casos de teste independentes].
Documente suposições e alterações; não invente resultados nem
modifique o protocolo para obter métricas mais altas.
```

### Registro de proveniência recomendado

| Campo | Conteúdo |
|---|---|
| Componente | Extrator, splitter, modelo, agregador ou medidor |
| Origem | Código próprio, terceiro, documentação ou geração assistida |
| Referência | DOI/URL, versão, commit e seção |
| Reutilização | Cópia, adaptação, reimplementação ou inspiração conceitual |
| Condições | Licença, atribuição e autorizações registradas |
| Alterações | Diferenças em relação à fonte e justificativa |
| Verificação | Testes, revisão humana e resultado |

## 13. F10 — Reprodutibilidade e artigo

- [ ] [CÓDIGO] Reconstruir tabelas e figuras a partir dos resultados brutos por um comando documentado.
- [ ] [CÓDIGO] Conferir que cada número do texto aponta para execução, split, modelo, métrica e arquivo de origem.
- [ ] [CÓDIGO] Reexecutar em ambiente limpo ao menos um fluxo completo representativo; comparar dentro das tolerâncias publicadas.
- [ ] [MANUAL] Disponibilizar configurações, splits, código e instruções conforme as licenças. Se dados não puderem ser redistribuídos, fornecer instrução de obtenção e checksum.
- [ ] [MANUAL] Registrar resultados negativos, falhas, exclusões justificadas e desvios de protocolo.
- [ ] [MANUAL] Separar números relatados na literatura de números reproduzidos na bancada própria.
- [ ] [MANUAL] Descrever o histórico exploratório e a ausência de teste externo verdadeiramente novo, se for o caso.
- [ ] [MANUAL] Revisar novidade, referências, autoria, uso de código e assistência por IA.

### Estrutura proposta do artigo

1. Introdução: tensão entre redes compactas, árvores quase perfeitas e modelos com contexto; perguntas e contribuições efetivamente demonstradas.
2. Trabalhos relacionados: R4 como contraponto neural leve, R7 como contraponto multi-dataset e R2 como contraponto relacional/temporal; protocolos e lacuna confirmada.
3. Dados e ameaças de validade: origem, atributos, `FlowID`, grupos, diferenças entre os datasets e auditoria.
4. Método experimental comum: splits, tuning, informação equivalente, métricas, custo e análise estatística.
5. E1 — Redes compactas versus árvores: modelos, ablações e benchmark computacional.
6. E2 — Suficiência do RF em múltiplos datasets: reprodução fiel, reprodução corrigida e limites de comparabilidade/transferência.
7. E3 — Valor do contexto: agregados tabulares versus representação relacional/temporal e custo da janela/grafo.
8. Implantação local versus borda: posições, rede, recursos, carga e falhas para modelos selecionados.
9. Discussão: qual hipótese foi sustentada em cada eixo, escolhas operacionais e generalização possível.
10. Limitações, disponibilidade de artefatos e conclusão sem extrapolação.

### Critérios para considerar o estudo pronto para redação final

- [ ] Existe uma lacuna delimitada após revisão, sem promessa de superioridade universal.
- [ ] Todos os modelos recebem dados compatíveis com a tarefa comparada.
- [ ] Splits e pré-processamento respeitam o protocolo em todos os níveis.
- [ ] Resultados podem ser recalculados e possuem incerteza adequadamente interpretada.
- [ ] A latência inclui fronteiras de medição claras e falhas visíveis.
- [ ] O ganho de complexidade foi testado por ablação e custo.
- [ ] Limitações de timestamps, identidade, simulação e hardware estão declaradas.
- [ ] Material de terceiros e auxílio de IA têm proveniência.
- [ ] Nenhum valor esperado, ilustrativo ou herdado do projeto antigo aparece como resultado novo.

## 14. Primeiras ações práticas, em ordem

1. [ ] Criar repositório/ambiente novo e guardar apenas referências necessárias do trabalho antigo.
2. [ ] Preencher `scope.md` e escolher o núcleo sem extensões.
3. [ ] Baixar dataset da fonte escolhida e registrar checksum/licença.
4. [ ] Obter R1–R4 e R7 completos; recuperar URLs/autoria dos dois notebooks Kaggle.
5. [ ] Enviar manualmente solicitações de metadados/código e registrar pendências.
6. [ ] Construir matriz de literatura e auditoria reproduzível dos dados.
7. [ ] Decidir CSV-only ou cenário com metadados; obter Drone IDS/ICSCASD-MPLC somente de fontes confirmadas.
8. [ ] Congelar S0/S1/S2 viáveis, métricas e orçamento antes de gerar código de treino extensivo.
9. [ ] Implementar Dummy, regressão logística e RF com testes metodológicos.
10. [ ] Completar Extra Trees, boosting, MLP e CNN residual; executar piloto de custo e decidir se stacking permanece como baseline secundário.
11. [ ] Executar E1 e E2; implementar E3 relacional/temporal apenas na forma autorizada pelos metadados disponíveis.
12. [ ] Congelar plano final de implantação e executar a bancada local versus borda.
13. [ ] Considerar encaminhamento seletivo ou federação somente após responder às perguntas do núcleo.

## 15. Documentações oficiais de consulta

As páginas `stable` podem mudar. No novo ambiente, registrar a versão instalada e usar documentação correspondente. Não copiar automaticamente versões do projeto antigo nem assumir que exemplos atuais funcionam em versões anteriores.

| Uso | Documentação |
|---|---|
| Pipelines e vazamento | [scikit-learn: common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html) |
| Divisões e grupos | [scikit-learn: cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html) |
| Seleção versus avaliação | [scikit-learn: nested CV](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html) |
| Stacking e OOF | [StackingClassifier](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.StackingClassifier.html) |
| Probabilidades | [scikit-learn: calibration](https://scikit-learn.org/stable/modules/calibration.html) |
| Métricas | [scikit-learn: model evaluation](https://scikit-learn.org/stable/modules/model_evaluation.html) |
| Restrições de recursos | [Docker Engine](https://docs.docker.com/engine/containers/resource_constraints/) |
| Emulação de rede | [tc-netem](https://man7.org/linux/man-pages/man8/tc-netem.8.html) |
| Medição neural | [PyTorch benchmark](https://docs.pytorch.org/tutorials/recipes/recipes/benchmark.html) |
| Reprodutibilidade neural | [PyTorch randomness](https://docs.pytorch.org/docs/stable/notes/randomness.html) |
| Extração de fluxos na simulação | [NS-3 FlowMonitor](https://www.nsnam.org/docs/models/html/flow-monitor.html) |

**Regra final:** escolher a conclusão a partir do experimento executado; nunca escolher ou alterar o experimento para sustentar uma conclusão já escrita.
