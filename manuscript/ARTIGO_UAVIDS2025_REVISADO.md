# Classificação de intrusões no UAVIDS-2025: partições de avaliação, atributos derivados e custo de inferência

## Resumo

O desempenho de classificadores de intrusões depende de como os dados são divididos e dos atributos usados na avaliação. Neste estudo, Random Forest e XGBoost foram avaliados em 122.171 fluxos do UAVIDS-2025, distribuídos em cinco classes. Foram comparadas divisões aleatórias estratificadas, por assinatura numérica e por endereço de origem, com os mesmos modelos e partições em cada tratamento. Três razões derivadas dos atributos originais foram testadas separadamente e em conjunto. Com os 18 atributos originais, o F1-macro do XGBoost foi 0,956326 na divisão aleatória e 0,952666 na separação por origem. Nesta última, os intervalos das diferenças de F1-macro entre os tratamentos derivados e a referência incluíram zero. A razão de pacotes perdidos por transmitidos reproduziu quase integralmente um atributo existente, enquanto a razão de vazão por salto ficou indefinida em 38.501 registros. A inferência de quatro modelos também foi medida em contêiner com 0,5 CPU e 512 MiB; o XGBoost apresentou mediana HTTP de 1,107 ms. Os resultados mostram como a escolha da partição e dos atributos afeta a interpretação do desempenho neste conjunto de dados.

Palavras-chave: UAV; detecção de intrusões; validação cruzada; atributos derivados; latência de inferência.

## Abstract

Intrusion-classifier performance depends on how data are partitioned and which features are used for evaluation. This study assessed Random Forest and XGBoost on 122,171 UAVIDS-2025 flows from five classes. Stratified random, exact numeric-signature-disjoint, and source-address-disjoint folds were compared using the same models and paired feature treatments. Three ratios derived from the original features were evaluated separately and jointly. With the 18 original features, XGBoost achieved a macro F1 of 0.956326 under random splitting and 0.952666 under source-disjoint evaluation. Under the latter protocol, the intervals for macro-F1 differences between the derived treatments and the reference included zero. The packet-loss ratio was nearly redundant with an existing feature, while throughput per hop was undefined for 38,501 records. Inference cost was also measured for four models in a container limited to 0.5 CPU and 512 MiB; XGBoost had a median HTTP latency of 1.107 ms. These results show how partition and feature choices affect performance interpretation within this dataset.

Keywords: UAV; intrusion detection; cross-validation; derived features; inference latency.

## 1. Introdução

Conjuntos públicos de dados permitem comparar classificadores de intrusões. O resultado, porém, depende da composição do treinamento e do teste: fluxos diferentes podem compartilhar endereços, condições de geração ou valores idênticos de atributos. Por isso, a escolha da partição integra a definição do problema avaliado.

O UAVIDS-2025 reúne fluxos de tráfego normal e de quatro tipos de ataque em uma rede simulada de veículos aéreos não tripulados (UAVs) [1,2]. Estudos anteriores avaliaram classificadores e analisaram erros nesse conjunto [1,3]. A separação de dados por origem também foi empregada em uma tarefa distinta de detecção de Sybil desconhecido [4]. Ainda cabe examinar, para a classificação das cinco classes originais, como diferentes partições e razões derivadas dos contadores de fluxo afetam os resultados sob um protocolo comum.

As perguntas do estudo são: quanto o desempenho muda quando o teste separa assinaturas numéricas ou endereços de origem, em vez de usar uma divisão aleatória? E as três razões derivadas melhoram a classificação nos mesmos modelos e partições? A análise inclui o desempenho por classe e o custo de inferência local de quatro modelos.

O estudo apresenta uma comparação pareada das partições e dos tratamentos de atributos, acompanhada da análise dos erros por classe e da medição de latência em ambiente limitado. Os resultados são interpretados segundo as características observadas no próprio conjunto de dados.

## 2. Trabalhos relacionados

Zeng, Bashir e Nait-Abdesselam apresentam o UAVIDS-2025 e resultados iniciais de classificação com divisão estratificada entre treinamento e teste [1]. O conjunto foi produzido por simulação no NS-3 e contém fluxos normais e de quatro ataques [2].

Zarkadis e Douligeris avaliam ensembles, modelos neurais e explicações de predições no mesmo conjunto de dados [3]. O estudo discute, entre outros resultados, erros entre Blackhole e Wormhole. A análise aqui apresentada acrescenta uma comparação das partições e das razões derivadas, mantendo fixos os modelos e o pré-processamento.

Demir e Gümüş usam separação por origem e uma representação de taxas para detectar ataques Sybil não vistos no treinamento [4]. Trata-se de uma tarefa de detecção de novidade; no presente estudo, as cinco classes permanecem no treinamento e no teste.

Islam et al. comparam modelos em bases de drones e redes industriais [5]. Na análise que apresentam para o UAVIDS-2025, são consideradas três classes: Normal, Blackhole e Wormhole. A diferença no número de classes reforça a necessidade de explicitar a tarefa antes de comparar métricas entre estudos.

## 3. Dados e métodos

### 3.1. Conjunto de dados e tarefa

Foi utilizado o UAVIDS-2025, disponibilizado no Zenodo sob licença CC BY 4.0 [2]. O arquivo contém 122.171 fluxos e 23 colunas, com 176 endereços de origem e 218 de destino distintos. Como esses endereços não identificam aeronaves individuais de forma verificável, a tarefa foi definida como classificação dos vetores de fluxo disponíveis no arquivo.

Cada vetor recebe uma das cinco classes originais. A Tabela 1 apresenta o número de fluxos por classe, preservado na agregação das predições fora da amostra.

Tabela 1. Composição do conjunto de dados e suporte das classes.

{{TABLE_CLASSES}}

### 3.2. Protocolos de avaliação

Foram comparados três protocolos de validação cruzada com cinco partições: divisão aleatória estratificada, separação por assinatura numérica e separação por endereço de origem. Em cada rodada, quatro partições foram usadas para treinamento e a restante para avaliação. A divisão aleatória preserva aproximadamente as proporções das classes. Na separação por assinatura, registros com valores idênticos nos 18 atributos originais permanecem no mesmo grupo. Na separação por origem, todos os fluxos associados ao mesmo endereço de origem permanecem juntos. As divisões por grupos também procuram preservar as proporções das classes; verificou-se a presença das cinco classes em todas as partições.

A divisão aleatória permite que origens e assinaturas apareçam no treinamento e no teste. A separação por assinatura impede a repetição exata do painel numérico entre as duas amostras. A separação por origem avalia fluxos de endereços não observados no treinamento, dentro do mesmo conjunto de dados.

As partições foram definidas antes da análise dos resultados e mantidas iguais entre modelos e tratamentos de atributos.

### 3.3. Tratamentos de atributos

O tratamento de referência utiliza os 18 atributos numéricos originais. Foram avaliadas três razões derivadas: pacotes perdidos por pacote transmitido (LostPackets/TxPackets), bytes recebidos por bytes transmitidos (RxBytes/TxBytes) e vazão por salto ((Throughput/Kbps)/AverageHopCount). Cada razão foi acrescentada individualmente ao painel original; um quarto tratamento acrescentou as três em conjunto. As duas primeiras razões são adimensionais, e a terceira é expressa em Kbps por salto.

Denominadores menores ou iguais a zero e resultados não finitos das razões geram valores ausentes; não se acrescentou uma constante ao denominador. A imputação pela mediana é ajustada exclusivamente nos dados de treinamento de cada partição e aplicada à avaliação. Uma variável derivada inteiramente ausente no treinamento é preservada e preenchida com zero. O tratamento de referência recebe o mesmo procedimento de imputação. Não há normalização, seleção de atributos ou ajuste estatístico usando os dados de avaliação. As razões não são recortadas na análise principal.

### 3.4. Modelos e orçamento experimental

Random Forest [6] e XGBoost [7] foram treinados com os parâmetros fixos apresentados no Quadro 1. Não houve busca de hiperparâmetros nem escolha de modelos com base no desempenho de teste. A avaliação foi implementada com scikit-learn [8] e utilizou quatro núcleos de processamento; as versões do ambiente estão registradas nos materiais de reprodução.

Quadro 1. Configuração dos classificadores na avaliação preditiva.

{{TABLE_MODELS}}

A análise principal compreendeu três protocolos, dois modelos, cinco tratamentos de atributos e cinco partições, totalizando 150 ajustes. A estabilidade foi examinada na separação por endereço de origem com três inicializações independentes para cada combinação de modelo, tratamento e partição (150 ajustes adicionais). Outros dez ajustes avaliaram, como análise de sensibilidade, o recorte da taxa de descarte de pacotes ao intervalo [0,1], mantendo os atributos originais. O recorte não foi adotado como correção dos dados.

### 3.5. Métricas e análise de incerteza

A medida principal é o F1-macro, calculado após concatenar as predições fora da amostra das cinco partições. Para cada classe c, VP(c), FP(c) e FN(c) representam, respectivamente, verdadeiros positivos, falsos positivos e falsos negativos, considerando as demais classes em conjunto. A precisão P(c), a revocação R(c) e o F1 da classe são definidos por:

$$
P(c) = VP(c) / [VP(c) + FP(c)]
$$

$$
R(c) = VP(c) / [VP(c) + FN(c)]
$$

$$
F1(c) = 2 P(c) R(c) / [P(c) + R(c)]
$$

O F1-macro é a média não ponderada do F1 das cinco classes, aqui indicadas por c₁ a c₅:

$$
F1-macro = [F1(c₁) + F1(c₂) + F1(c₃) + F1(c₄) + F1(c₅)] / 5
$$

Quando o denominador de uma dessas expressões é zero, a métrica correspondente recebe zero. Também foram obtidas contagens de confusão e duas taxas específicas da tarefa:

$$
Taxa de falsos alarmes = N(normal → ataque) / N(normal)
$$

$$
Taxa de ataques perdidos = N(ataque → normal) / N(ataque)
$$

N(·) indica o número de fluxos na condição entre parênteses. Confusões entre tipos de ataque não entram nos numeradores dessas duas taxas.

Cada tratamento com razões derivadas foi comparado ao tratamento de referência por diferenças pareadas no F1-macro:

$$
ΔF1-macro = F1-macro(tratamento) − F1-macro(referência)
$$

A incerteza foi estimada com 2.000 réplicas de bootstrap de grupos e intervalos percentis de 95%. Em cada réplica, grupos são sorteados com reposição; todos os seus fluxos permanecem juntos, e o mesmo sorteio é usado nos dois tratamentos. A unidade de reamostragem é o endereço de origem na divisão aleatória e na separação por origem, e a assinatura numérica exata na separação por assinatura.

Os intervalos descrevem a variação das diferenças nas predições obtidas neste conjunto de dados. Um intervalo que inclui zero indica que o procedimento não distinguiu o tratamento da referência; não estabelece equivalência entre eles.

### 3.6. Medição da latência

O custo de inferência foi medido para regressão logística, MLP compacta, XGBoost e Random Forest em contêineres Linux. O F1-macro exibido junto às latências vem da validação cruzada com endereços de origem separados. Para a medição de tempo, cada modelo foi reajustado com todos os fluxos e servido por HTTP local. Assim, qualidade preditiva e latência se referem ao mesmo tipo de modelo, mas a etapas experimentais distintas.

Cada contêiner recebeu limites de 0,5 CPU e 512 MiB, com uma thread de inferência. Os quatro modelos receberam a mesma sequência de entradas. Após 200 chamadas de aquecimento, foram registradas 5.000 requisições individuais por modelo. O tempo HTTP vai do envio do vetor já serializado à leitura da resposta, incluindo o processamento do serviço e a predição. A extração do fluxo e o cálculo dos atributos não fazem parte dessa medida.

As medições foram feitas em uma sessão, na mesma máquina e com ordem fixa dos modelos. A memória apresentada corresponde ao maior valor registrado durante a amostragem do contêiner.

Figura 1. Protocolos de validação preditiva e medição do custo de inferência. A estimativa de qualidade vem da avaliação por separação de endereços de origem; as latências vêm do benchmark local de inferência.

{{FIGURE_METHOD}}

## 4. Resultados

### 4.1. Desempenho segundo o protocolo de avaliação

A Tabela 2 mostra o desempenho com os 18 atributos originais. Para ambos os modelos, o F1-macro foi menor na separação por origem do que na divisão aleatória estratificada: a diferença foi de −0,437 ponto percentual para Random Forest e −0,366 para XGBoost. A separação por assinatura numérica apresentou valores intermediários.

Tabela 2. F1-macro fora da amostra com os 18 atributos numéricos originais.

{{TABLE_PROTOCOLS}}

Os três protocolos avaliam populações de teste diferentes. A leitura dos escores deve, portanto, considerar quais origens ou assinaturas puderam aparecer no treinamento.

### 4.2. Efeito dos atributos derivados

Na separação por endereço de origem, os oito intervalos das diferenças entre os tratamentos derivados e a referência incluem zero (Tabela 3). Nos três protocolos, apenas dois dos 24 intervalos excluem zero; ambos correspondem a diferenças negativas para Random Forest na separação por assinatura, quando a razão entre pacotes perdidos e transmitidos é incluída. As razões propostas, portanto, não mostraram ganho consistente nos modelos e partições avaliados.

Tabela 3. Diferenças de F1-macro na separação por endereço de origem em relação ao painel de referência com atributos originais. Valores em pontos percentuais; intervalos condicionais de 95%.

{{TABLE_ABLATION}}

A repetição com três inicializações manteve a magnitude pequena das diferenças. Para Random Forest, acrescentar vazão por salto produziu diferença média de +0,051 ponto percentual em relação à referência; para XGBoost, a média foi +0,006 ponto percentual e o sinal variou entre inicializações. Em 21 dos 24 contrastes pareados, o intervalo incluiu zero.

### 4.3. Análise das razões derivadas

A razão entre pacotes perdidos e transmitidos coincide aproximadamente com o atributo PacketDropRate em 122.148 dos 122.171 registros. Sua inclusão acrescenta, portanto, pouca informação ao painel original.

A razão de vazão por salto é indefinida em 38.501 fluxos, ou 31,5% do conjunto. A proporção é maior nas classes Normal (51,3%) e Blackhole (48,8%). Por isso, sua inclusão combina os valores calculados com o efeito da imputação nos registros sem denominador válido.

O arquivo contém 81 valores de PacketDropRate acima de um. A análise principal manteve esses valores. Em uma análise de sensibilidade, o recorte ao intervalo [0,1] mudou o F1-macro da separação por origem em +0,043 ponto percentual para Random Forest e +0,003 para XGBoost; os intervalos das duas diferenças incluíram zero.

### 4.4. Erros por classe

A Tabela 4 detalha o XGBoost com os 18 atributos originais na separação por origem. Blackhole apresentou revocação de 0,861241; seu F1 e o de Wormhole ficaram abaixo dos valores das demais classes. A média global, portanto, convive com dificuldades específicas de classificação, também discutidas por Zarkadis e Douligeris [3].

Tabela 4. Desempenho por classe para o XGBoost com os atributos originais na separação por endereço de origem.

{{TABLE_ERRORS}}

Entre os 95.999 fluxos de ataque, 281 foram classificados como normais (0,293%). Entre os 26.172 fluxos normais, 231 foram classificados como ataque (0,883%). Esses percentuais correspondem às taxas definidas na metodologia.

### 4.5. Qualidade preditiva e custo de inferência

A Tabela 5 reúne o F1-macro fora da amostra na separação por origem e a latência HTTP medida no contêiner. XGBoost apresentou o maior F1-macro (0,952666), com mediana de 1,107 ms. Random Forest teve F1-macro de 0,950677, mediana de 5,856 ms e P95 de 51,302 ms. A MLP apresentou latência próxima à regressão logística e F1-macro maior.

Tabela 5. F1-macro fora da amostra na separação por endereço de origem e custo HTTP em contêiner com 0,5 CPU e 512 MiB.

{{TABLE_LATENCY}}

No ambiente medido, XGBoost combinou o maior F1-macro com latência mediana menor que a de Random Forest. Para este último, o P95 e o consumo de memória também foram mais altos, indicando que a escolha do modelo deve considerar a distribuição dos tempos e o limite de recursos disponível.

Figura 2. F1-macro fora da amostra na separação por endereço de origem e percentis de latência HTTP medidos no benchmark local. O eixo do F1-macro mostra o intervalo de 0,8 a 1,0; o painel de latência usa escala logarítmica. As métricas de qualidade e latência têm origens experimentais distintas.

{{FIGURE_PERF}}

## 5. Discussão

A separação por origem reduziu o F1-macro dos dois classificadores em relação à divisão aleatória, embora os valores tenham permanecido altos. Como cada partição define quais fluxos podem compartilhar padrões entre treinamento e teste, o protocolo de avaliação deve acompanhar qualquer resultado relatado para o conjunto.

As razões derivadas não produziram ganho consistente. A razão entre pacotes perdidos e transmitidos repetiu quase totalmente uma variável existente, enquanto a vazão por salto exigiu imputação em parcela expressiva do conjunto. Esses resultados mostram que acrescentar atributos com interpretação intuitiva não implica, por si só, ampliar a informação disponível para os modelos.

Na medição de custo, XGBoost apresentou uma combinação favorável de F1-macro e latência mediana sob os limites de recursos adotados. Os estudos relacionados empregam diferentes classes e protocolos [3–5]; o presente resultado acrescenta uma comparação controlada dentro da tarefa de cinco classes do UAVIDS-2025.

## 6. Conclusão

No UAVIDS-2025, a separação por origem resultou em F1-macro menor que a divisão aleatória para Random Forest e XGBoost. As três razões derivadas não melhoraram de forma consistente os classificadores; uma delas reproduziu quase integralmente um atributo original e outra apresentou muitos valores indefinidos. Na comparação de custo local, XGBoost reuniu o maior F1-macro e latência mediana menor que a de Random Forest.

Em trabalhos futuros, a comparação poderá ser ampliada para execuções independentes da simulação e para a medição conjunta da extração de atributos e da inferência em plataformas embarcadas.

## Referências

[1] Zeng, Q.; Bashir, A.; Nait-Abdesselam, F. UAVIDS-2025: A Benchmark Dataset for Intrusion Detection in UAV Networks Using Machine Learning Techniques. IEEE Conference on Communications and Network Security (CNS), 2025, p. 1–9. https://doi.org/10.1109/CNS66487.2025.11194990.

[2] Zeng, Q.; Bashir, A.; Nait-Abdesselam, F. UAVIDS-2025. Conjunto de dados, versão 1. Zenodo, 2025. https://doi.org/10.5281/zenodo.15336998.

[3] Zarkadis, I.-C.; Douligeris, C. XAI and Statistical Analysis for Reliable Intrusion Detection in the UAVIDS-2025 Dataset: From Tree to Hybrid and Tabular DNN Ensembles. arXiv:2605.13922, 2026. https://doi.org/10.48550/arXiv.2605.13922.

[4] Aksu Demir, I. E.; Gümüş, F. Source-Rate Representations and Attention Autoencoders for Leakage-Safe Zero-Day Sybil Detection in UAV Networks. Electronics, v. 15, n. 17, artigo 3966, 2026. https://doi.org/10.3390/electronics15173966.

[5] Islam, M. S.; Ahmed, F.; Ishtiaq, W.; Hossain, M. A.; Islam, M. S.; Tarek, M. M. Advanced explainable ensemble models for multi-class intrusion detection in heterogeneous drone and industrial networks. Journal on Information Security, v. 2026, artigo 14, 2026. https://doi.org/10.1186/s13635-026-00234-w.

[6] Breiman, L. Random Forests. Machine Learning, v. 45, p. 5–32, 2001. https://doi.org/10.1023/A:1010933404324.

[7] Chen, T.; Guestrin, C. XGBoost: A Scalable Tree Boosting System. Proceedings of the 22nd ACM SIGKDD International Conference on Knowledge Discovery and Data Mining, p. 785–794, 2016. https://doi.org/10.1145/2939672.2939785.

[8] Pedregosa, F. et al. Scikit-learn: Machine Learning in Python. Journal of Machine Learning Research, v. 12, p. 2825–2830, 2011. https://www.jmlr.org/papers/v12/pedregosa11a.html.
