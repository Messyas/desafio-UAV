# Plano científico: generalização e eficiência operacional de IDS no UAVIDS-2025

Data: 7 de setembro de 2026. Versão inicial: 1.0.

Este documento especifica um projeto novo, a ser implementado do zero. Ele não valida o código antigo, não autoriza sua exclusão automática e não contém resultados novos de treinamento. Os notebooks anteriores servem apenas como material exploratório e fonte de hipóteses. DVC e a API antiga não fazem parte da contribuição científica proposta.

Título de trabalho: **Além da divisão aleatória: identificadores, generalização por origem e custo de inferência no UAVIDS-2025**.

A contribuição desta versão é uma avaliação reproduzível de como identificadores, protocolo de divisão e custo de atendimento em Docker local afetam a escolha entre Random Forest e XGBoost. Por decisão registrada em 8 de setembro de 2026, CNN, GNN, stacking, Kubernetes e emulação de rede não integram o núcleo. Superioridade, novidade e viabilidade embarcada não são conclusões antecipadas.

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
- [x] F4 — Congelar protocolos de divisão, tuning e análise. Evidência: `protocol/evaluation_v1.md`, `configs/nested_tuning_v2.json` e splits persistidos.
- [x] F5 — Implementar baselines e testes de integridade metodológica. Evidência: `src/uavids_study/` e `tests/`.
- [x] F6 — Executar comparação preditiva e ablação de identificador. Evidência: `results/predictive_baseline_v1/`, `reports/nested_tuning_v2/` e `reports/stability_v1/`.
- [x] F7 — Congelar modelos e executar benchmark Docker local. Evidência: `protocol/docker_local_v2.md`, `benchmarks/docker_local_v2/` e `reports/docker_local_v2/`.
- [x] F8 — Avaliar extensões e retirá-las desta versão por decisão de escopo registrada.
- [ ] F9 — Analisar resultados, limitações e incertezas.
- [ ] F10 — Reproduzir a execução e escrever o artigo.

F1 e a obtenção de F2 podem avançar juntas. F9 e F10 permanecem necessários para a submissão. CNN, GNN, LSTM, stacking, múltiplos datasets, Kubernetes, emulação de rede e tempo até detectar ataques estão fora do escopo desta versão.

## 2. F0 — Escopo científico

### Perguntas de pesquisa

| ID | Pergunta | Evidência necessária |
|---|---|---|
| P1 | Quanto `FlowID` altera o desempenho aparente no UAVIDS-2025? | Ablação pareada com e sem o identificador, sem usar o resultado diagnóstico para selecionar o painel principal |
| P2 | Quanto as conclusões mudam entre divisão aleatória, assinaturas repetidas e origens não vistas? | S0, S1 e S2 com índices persistidos, preprocessamento dentro do treino e métricas por classe |
| P3 | Entre Random Forest e XGBoost com qualidade semelhante, qual oferece a melhor fronteira local de qualidade e custo? | Estabilidade preditiva e benchmark Docker controlado de latência, vazão, memória, CPU e tamanho |

### Dois eixos centrais do artigo

#### Eixo I — Robustez da avaliação tabular

O estudo quantifica o efeito de `FlowID` e compara S0, S1 e S2. O objetivo é mostrar quais conclusões dependem do identificador, de padrões repetidos ou da capacidade de generalizar para origens não vistas.

#### Eixo II — Fronteira local de qualidade e custo

Random Forest e XGBoost são comparados após seleção e congelamento dos artefatos. O benchmark Docker mede vetores de 18 atributos já calculados, em loopback e sob limites iguais de CPU e memória. R4 permanece como contraponto bibliográfico sobre modelos compactos, sem reprodução experimental de sua CNN.

- [x] [MANUAL] Adotar cinco classes como tarefa principal: Normal, Blackhole, Flooding, Sybil e Wormhole.
- [x] [MANUAL] Registrar unidade predita: um registro de fluxo com atributos disponíveis no momento definido pelo experimento.
- [x] [MANUAL] Definir população de interesse: novos registros da mesma distribuição, novas origens ou novas execuções de simulação. Não tratar essas populações como equivalentes.
- [x] [MANUAL] Manter binário e quatro classes como análises secundárias, se houver orçamento.
- [x] [MANUAL] Excluir desta versão: CNN, GNN, LSTM, stacking, múltiplos datasets, ataques desconhecidos, aprendizado federado, votação bizantina, Kubernetes e emulação de rede.
- [ ] [MANUAL] Registrar equipamento disponível, horas de processamento, disponibilidade de Linux e acesso eventual a uma placa embarcada.
- [ ] [MANUAL] Selecionar publicação-alvo provisória e consultar exigências de dados, código, uso de IA e extensão do artigo no site oficial escolhido.
- [ ] [REVISÃO] Verificar se a contribuição ainda se diferencia dos trabalhos da F1. Não prometer publicação nem ineditismo antes desta revisão.

**Entregável:** `protocol/scope.md`, com perguntas, exclusões, orçamento, responsáveis e data.

### Resultados que também são cientificamente válidos

- Um baseline simples permanecer melhor após tuning equilibrado.
- O ranking mudar entre protocolos, sem que um deles represente uma verdade universal.
- Random Forest e XGBoost apresentarem qualidade equivalente, mas custos operacionais muito diferentes.

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

### Como os contrapontos entram na contextualização

Não copiar as formulações abaixo literalmente para o artigo final antes de concluir a reprodução. Elas registram a lógica argumentativa e devem ser reescritas com os resultados efetivamente obtidos.

1. **Custo precisa de uma fronteira explícita.** R4 relata alta qualidade e baixo custo para uma CNN residual. A presente pesquisa não reproduz essa arquitetura; usa o trabalho para justificar a separação entre tempo interno do estimador, latência HTTP, tamanho e memória, sem comparar diretamente números medidos em bancadas diferentes.
2. **Resultados quase perfeitos exigem auditoria de identificadores.** R7 relata RF como melhor modelo em três datasets. No caso do UAVIDS-2025, seu artigo apresenta `FlowID` como atributo importante apesar de o fluxograma indicar remoção de identificadores. Essa tensão motiva a ablação pareada usada aqui.
3. **Amostras independentes têm alcance limitado.** R2 argumenta a favor de contexto topológico e temporal. Como o CSV local não fornece metadados suficientes para reproduzir esse cenário com rigor, o trabalho é citado como limitação e direção futura, sem experimento GNN ou temporal.

Formulação metodológica segura:

> Em contrapartida a resultados quase perfeitos cuja documentação deixa ambíguo o uso de identificadores, esta pesquisa mede explicitamente o efeito de `FlowID`, compara populações de teste distintas e avalia Random Forest e XGBoost sob a mesma fronteira Docker local.

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
| XGBoost | Boosting e candidato operacional | Mesmos atributos, splits, orçamento e limites de serviço |

Modelos adicionais executados durante exploração podem aparecer em material suplementar, desde que identificados como exploratórios. A comparação confirmatória e o benchmark de sistemas desta versão se limitam a Random Forest e XGBoost.

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

### Desenho dos experimentos centrais

| Experimento | Pergunta principal | Tratamentos mínimos | Controle decisivo | Resultado que refuta a hipótese do projeto |
|---|---|---|---|---|
| E1 — Identificador | `FlowID` infla o desempenho aparente? | Avaliação pareada com e sem `FlowID` | Mesmo split, estimador e orçamento | A remoção não altera materialmente as métricas |
| E2 — Generalização | A conclusão permanece em S0, S1 e S2? | RF e XGBoost nos splits congelados | Mesmo contrato de atributos e tuning interno | A ordenação muda ou o desempenho cai sob grupos mais exigentes |
| E3 — Docker local | Qual modelo oferece a melhor fronteira qualidade–custo? | RF e XGBoost congelados, batch 1 e lotes | Mesma imagem-base, 0,5 CPU, 512 MiB e carga repetida | A diferença de custo é pequena ou contradiz a escolha preditiva |

- [x] [CÓDIGO] Produzir dois resultados diagnósticos inspirados em R7 no UAVIDS-2025: com `FlowID` e sem `FlowID`, sem chamar a execução de reprodução fiel sem o código original.
- [x] [CÓDIGO] Não usar desempenho com `FlowID` para selecionar features ou ajustar o painel principal.
- [ ] [MANUAL] Tratar a aparente inconsistência de R7 como questão de reprodutibilidade até examinar código ou obter resposta dos autores; não alegar erro metodológico como fato consumado.

### Ablações planejadas

| ID | Comparação | Fatores a manter constantes |
|---|---|---|
| A7 | Com `FlowID` × sem `FlowID` | Reprodução diagnóstica de R7; resultado principal sempre sem identificador |

- [x] Manter o resultado principal sem `FlowID` e tratar sua inclusão apenas como diagnóstico metodológico.
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

## 9. F7 — Benchmark de inferência Docker local

### Definir o que é medido

| Medida | Início → fim | Condição |
|---|---|---|
| Tempo do modelo | Entrada pronta do estimador → saída | Exclui extração e comunicação |
| Tempo do pipeline | Vetor bruto disponível → predição | Inclui derivadas, codificação e pré-processamento |
| Latência da requisição | Envio pelo cliente → resposta recebida | Inclui serialização, rede, fila e pipeline |

Reproduzir linhas do CSV em uma agenda artificial mede atendimento de vetores de fluxo. Não reproduz a cronologia original nem o efeito de perda/jitter sobre os atributos que originaram o CSV.

- [x] [MANUAL] Definir o cenário como um cliente representativo enviando vetores de fluxo já calculados a um serviço no Docker local; não representa inferência embarcada no UAV.
- [x] [MANUAL] Definir HTTP/1.1 em loopback, JSON com até 1.024 vetores de 18 atributos, conexões persistentes, sem TLS e timeout de 30 s. Não há retry automático.
- [ ] [MANUAL] Fixar critério operacional de prazo com fonte/justificativa. Na ausência de requisito real, usar análise de sensibilidade, sem chamar valores arbitrários de SLA de voo.
- [x] [CÓDIGO] Selecionar candidatos pelo desenvolvimento, ajustar artefatos para benchmark em todos os dados depois da avaliação e congelar hashes antes da medição. Esses artefatos não produzem métricas preditivas de treino.
- [x] [CÓDIGO] Usar no container os mesmos hashes de XGBoost e Random Forest congelados para o piloto local em processo.
- [x] [CÓDIGO] Comparar os dois modelos sob o mesmo serviço e os mesmos limites, declarando que família e tamanho do artefato variam juntos.

### Bancada e controles

- [x] [MANUAL] Registrar Docker Desktop 4.66.1, Engine 29.3.1, kernel WSL2 Linux/amd64 e host Windows no manifesto. A quota não é equiparada a ARM.
- [x] [CÓDIGO] Executar gerador e coleta no host e um container de inferência separado por modelo; preservar throughput observado para detectar gargalo da bancada.
- [x] [CÓDIGO] Aplicar 0,5 CPU, 512 MiB, uma thread numérica e 256 PIDs; persistir os limites observados pelo Docker.
- [x] [CÓDIGO] Executar em loopback sem degradação artificial de rede e declarar essa fronteira.

Documentação: [recursos do Docker](https://docs.docker.com/engine/containers/resource_constraints/). A limitação de recursos não reproduz automaticamente rádio, mobilidade, ARM ou consumo energético de drones.

### Matriz congelada do benchmark local

| Fator | Níveis iniciais sugeridos |
|---|---|
| CPU | 0,5 CPU equivalente em quota |
| RAM | 512 MiB |
| Rede | HTTP em loopback, sem emulação |
| Batch | 1, 32, 256 e 1024 |
| Concorrência | 1, 4 e 8 clientes |
| Repetições | 5 por condição, após 200 chamadas de aquecimento |

Essa matriz caracteriza apenas o computador e o Docker registrados no manifesto. Ela não representa um perfil de enlace UAV.

### Medição rigorosa

- [x] [CÓDIGO] Usar `perf_counter_ns` monotônico e IDs de repetição/chamada. Medir ida/volta no mesmo cliente e tempo interno separadamente.
- [x] [CÓDIGO] Separar carregamento, aquecimento e regime estável no piloto local.
- [x] [CÓDIGO] Medir chamada individual e lotes separadamente. O custo dividido pelo lote foi rotulado como amortizado.
- [x] [CÓDIGO] Registrar sucessos e falhas, P50/P95/P99, vazão, CPU e RAM. Não definir prazo operacional sem requisito externo.
- [x] [CÓDIGO] Realizar cinco repetições, 200 chamadas de aquecimento e 5.000 medições HTTP individuais por modelo, além de 600 chamadas em lote e 4.500 chamadas de throughput.
- [x] [CÓDIGO] Executar em ordem determinística registrada; tratar temperatura e atividade externa não controladas como limitação da bancada local.
- [x] [CÓDIGO] Preservar medições individuais em formato estruturado; tabelas foram geradas delas.
- [x] [REVISÃO] Não afirmar consumo de energia ou bateria: a bancada mede CPU e RAM, sem instrumento de potência.

**Critério de conclusão F7:** há evidência de que carga, limites e perfis foram efetivamente aplicados, além de medições reproduzíveis e fronteiras claras do tempo medido.

## 10. F8 — Extensões retiradas desta versão

CNN, GNN, modelos temporais, stacking, outros datasets, inferência na borda, `tc-netem`, Kubernetes, aprendizado federado e ataques não vistos não participam dos experimentos nem sustentam as conclusões. R2, R4, R6 e R7 podem ser discutidos como literatura relacionada e motivação de controles, sempre distinguindo resultados publicados de resultados obtidos neste repositório.

## 11. F9 — Estatística e interpretação

- [ ] [MANUAL] Fixar como contraste principal a diferença pareada de F1-macro entre XGBoost e Random Forest em S2; tratar custo Docker como contraste operacional complementar.
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

1. Introdução: risco de resultados quase perfeitos associados a identificadores e necessidade de avaliar simultaneamente generalização e custo de atendimento.
2. Trabalhos relacionados: benchmark original, alegações de Random Forest quase perfeito e estudos de implantação eficiente tratados apenas como contexto.
3. Dados e ameaças de validade: origem, atributos, `FlowID`, grupos e auditoria.
4. Método experimental comum: splits, tuning, informação equivalente, métricas, custo e análise estatística.
5. Resultados preditivos: S0/S1/S2, ablação de `FlowID`, tuning e estabilidade de RF/XGBoost.
6. Benchmark Docker local: latência HTTP e interna, lotes, throughput, CPU, RAM e tamanho dos artefatos.
7. Discussão: fronteira qualidade–custo, limites de generalização e implicações da dependência de identificadores.
8. Limitações, disponibilidade de artefatos e conclusão sem extrapolação.

### Critérios para considerar o estudo pronto para redação final

- [ ] Existe uma lacuna delimitada após revisão, sem promessa de superioridade universal.
- [ ] Todos os modelos recebem dados compatíveis com a tarefa comparada.
- [ ] Splits e pré-processamento respeitam o protocolo em todos os níveis.
- [ ] Resultados podem ser recalculados e possuem incerteza adequadamente interpretada.
- [ ] A latência inclui fronteiras de medição claras e falhas visíveis.
- [ ] A escolha entre RF e XGBoost foi examinada em qualidade, estabilidade e custo local.
- [ ] Limitações de timestamps, identidade, simulação e hardware estão declaradas.
- [ ] Material de terceiros e auxílio de IA têm proveniência.
- [ ] Nenhum valor esperado, ilustrativo ou herdado do projeto antigo aparece como resultado novo.

## 14. Primeiras ações práticas, em ordem

1. [x] Auditar o CSV local e registrar checksum, schema e limitações.
2. [x] Congelar S0/S1/S2, métricas e contratos de atributos.
3. [x] Executar baselines, ablação de `FlowID`, tuning e estabilidade.
4. [x] Congelar Random Forest e XGBoost para a comparação operacional.
5. [x] Executar e validar o benchmark Docker local v2.
6. [ ] Fechar a matriz de literatura, autoria dos notebooks e diferenças em relação a R1–R4/R7.
7. [ ] Definir contrastes, margens práticas e análise de incerteza sem usar requisições correlacionadas como réplicas independentes.
8. [ ] Gerar tabelas e figuras finais diretamente dos artefatos preservados.
9. [ ] Reescrever o artigo no escopo final e conferir cada alegação contra sua fonte.
10. [ ] Reproduzir ao menos um fluxo completo em ambiente limpo e preparar o pacote de submissão.

## 15. Documentações oficiais de consulta

As páginas `stable` podem mudar. No novo ambiente, registrar a versão instalada e usar documentação correspondente. Não copiar automaticamente versões do projeto antigo nem assumir que exemplos atuais funcionam em versões anteriores.

| Uso | Documentação |
|---|---|
| Pipelines e vazamento | [scikit-learn: common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html) |
| Divisões e grupos | [scikit-learn: cross-validation](https://scikit-learn.org/stable/modules/cross_validation.html) |
| Seleção versus avaliação | [scikit-learn: nested CV](https://scikit-learn.org/stable/auto_examples/model_selection/plot_nested_cross_validation_iris.html) |
| Probabilidades | [scikit-learn: calibration](https://scikit-learn.org/stable/modules/calibration.html) |
| Métricas | [scikit-learn: model evaluation](https://scikit-learn.org/stable/modules/model_evaluation.html) |
| Restrições de recursos | [Docker Engine](https://docs.docker.com/engine/containers/resource_constraints/) |
| Extração de fluxos na simulação | [NS-3 FlowMonitor](https://www.nsnam.org/docs/models/html/flow-monitor.html) |

**Regra final:** escolher a conclusão a partir do experimento executado; nunca escolher ou alterar o experimento para sustentar uma conclusão já escrita.
