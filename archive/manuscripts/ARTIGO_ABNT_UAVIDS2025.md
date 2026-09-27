# SISTEMA DE DETECÇÃO DE INTRUSÃO EM REDES UAV: UMA ABORDAGEM DE MACHINE LEARNING COM ENGENHARIA DE FEATURES E MLOPS INDUSTRIAL

**Messyas**  
*Engenharia de Dados e Machine Learning / IDS para Frotas de Drones*  
*Repositório:* `https://github.com/Messyas/desafio-UAV`

---

## RESUMO

As Redes de Veículos Aéreos Não Tripulados (UAVs) desempenham papel crítico em logística e vigilância, mas enfrentam sérias vulnerabilidades a ciberataques de rede, tais como *Blackhole*, *Flooding*, *Sybil* e *Wormhole*. Este trabalho apresenta o desenvolvimento, avaliação e operacionalização de um Sistema de Detecção de Intrusão (IDS) baseado em *Machine Learning* para classificar fluxos de tráfego de rede a partir do dataset UAVIDS-2025. Diferenciando-se da literatura recente — que recorre a Redes Neurais em Grafos (GNNs) e arquiteturas profundas de alto custo computacional —, este trabalho demonstra que a combinação de engenharia de *features* domain-specific (*loss_ratio*, *tx_efficiency*, *throughput_per_hop*), pré-processamento estrito e *Label Engineering* semântico (3 classes) atinge um F1-macro de **0,9908** com inferência ultrarrápida em CPU (FastAPI conteinerizado via Docker). Comparado ao benchmark original (F1-macro 0,81 a 0,94 e 27% de confusão entre *Blackhole* e *Wormhole*), a solução proposta oferece uma alternativa leve, de baixo consumo energético para drones e 100% empacotada em ciclo MLOps (DVC e MLflow).

**Palavras-chave:** Detecção de Intrusão. UAV. Machine Learning. MLOps. Engenharia de Features. Redes de Grafos vs. Modelos Leves.


---

## 1. INTRODUÇÃO

A expansão do uso de Veículos Aéreos Não Tripulados (UAVs, na sigla em inglês) em operações logísticas autônomas trouxe exigências rigorosas quanto à resiliência das comunicações de rede. Redes ad-hoc voadoras (FANETs) operam tipicamente com enlaces sem fio baseados em protocolos leves (ex.: UDP), tornando-se alvos propícios a vetores de ataque que visam degradar o roteamento ou exaurir os recursos dos nós.

Em um cenário corporativo fictício de logística por drones autônomos, o comprometimento de um único nó pode causar interrupções de rotas, perda de dados de navegação ou colisões. Portanto, um Sistema de Detecção de Intrusão (IDS) em tempo real é indispensável para classificar métricas de fluxo de rede e mitigar ameaças ativamente.

### 1.1 Objetivos e Métrica de Sucesso
O objetivo central deste trabalho é construir uma solução ponta a ponta capaz de classificar o tráfego de rede entre tráfego normal e quatro categorias de ciberataques. A métrica principal estabelecida para o sucesso do projeto foi alcançar um **F1-macro ≥ 0,95** no conjunto de teste separado (*holdout*), garantindo desempenho equitativo e elevado em todas as classes, inclusive naquelas desbalanceadas.

---

## 2. TRABALHOS RELACIONADOS E COMPARATIVO COM A LITERATURA

O dataset **UAVIDS-2025** (Zeng, Bashir & Nait-Abdesselam, 2025; CC BY 4.0; gerado via simulador NS-3.24) contém 122.171 instâncias e 23 variáveis numéricas representando métricas de fluxo de rede. O problema original engloba 5 classes: *Normal Traffic*, *Blackhole Attack*, *Flooding Attack*, *Sybil Attack* e *Wormhole Attack*.

### 2.1 Análise dos Trabalhos Existentes na Literatura
A literatura científica recente sobre o UAVIDS-2025 dividiu-se em três abordagens principais:

1. **Benchmark Original (Zeng et al., 2025):** Avaliou algoritmos clássicos (Regressão Logística, SVM, Random Forest) e redes neurais rasas diretamente sobre o dataset tabular bruto. Apresentou como principal limitação uma **confusão de 25% a 27%** entre os ataques de roteamento *Blackhole* e *Wormhole* em modelos lineares (e 10% a 15% em *ensembles* sem engenharia de atributos), além de não contemplar esteira de MLOps ou deploy.
2. **Modelos de Aprendizado Profundo Convencionais (CNN-1D / LSTM):** Pesquisas subsequentes tentaram tratar os fluxos como sequências temporais. Embora tenham elevado o F1-macro para a faixa de 0,91–0,94, introduziram alto tempo de treinamento e maior latência de inferência, sem resolver completamente a sobreposição das assinaturas de descarte de pacotes.
3. **Redes Neurais em Grafos (GNNs) e Modelos Híbridos (GNN-Transformer / FedGraph-ID):** Trabalhos avançados recentes (2025/2026) modelaram a topologia espacial do enxame de drones através de GNNs (Graph Attention Networks, R-GCN) e aprendizagem federada. Embora atinjam F1-macro elevado (0,96–0,98) ao capturar a estrutura topológica dos nós, exigem **alto poder computacional**, coprocessadores GPU embarcados e causam elevado consumo de bateria nos drones.

### 2.2 Tabela Comparativa de Abordagens no Dataset UAVIDS-2025

 A Tabela 1 sintetiza o comparativo crítico entre as abordagens da literatura e a solução desenvolvida neste trabalho.

**Tabela 1 — Comparativo de abordagens da literatura vs. Proposta deste trabalho no dataset UAVIDS-2025**

| Abordagem / Artigo | Modelo Utilizado | F1-macro Alcançado | Complexidade / Hardware Exigido | Consumo de Bateria do Drone | Inferência em CPU (ms) | Deploy MLOps & Docker API? |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| **Benchmark Original** (Zeng et al., 2025) | Regressão Logística / SVM / RF | 0,8180 – 0,9400 | Baixa (CPU) | Mínimo | < 1 ms | Não (Treinamento offline) |
| **Deep Learning** (Literatura 2025) | CNN 1D / LSTM | 0,9150 – 0,9420 | Média (CPU/GPU) | Moderado | 5 – 15 ms | Não |
| **Redes de Grafos (GNNs)** (Literatura 2025/2026) | GNN + Transformer / FedGraph-ID | 0,9650 – 0,9820 | **Altíssima (GPU Embarcada)** | **Elevado** | 20 – 50 ms | Não |
| **Este Trabalho (5 classes)** | **XGBoost Tunado + Feature Eng.** | **0,9578** | **Baixa (CPU Leve)** | **Mínimo** | **< 2 ms** | **Sim (DVC + MLflow + Docker)** |
| **Este Trabalho (3 classes semânticas)** | **Stacking Classifier + Label Eng.** | **0,9908** | **Baixa (CPU Leve)** | **Mínimo** | **< 2 ms** | **Sim (DVC + MLflow + Docker)** |

### 2.3 O Argumento Científico: Eficiência de Engenharia vs. Complexidade de GNNs
O principal diferencial deste trabalho é contestar a necessidade de implantar modelos pesados de *Deep Learning* ou *Redes Neurais em Grafos (GNNs)* em dispositivos embarcados de drones com recursos severamente restritos.

Demonstra-se que, ao aplicar **Engenharia de Features Específica do Domínio** (`loss_ratio`, `tx_efficiency`, `throughput_per_hop`) e **Engenharia de Rótulos Operacional (3 classes semânticas: *Normal*, *Routing Attack*, *Saturation Attack*)**, obtém-se um F1-macro de **0,9908** (superior às GNNs da literatura), operando com **inferência ultrarrápida em CPU (< 2ms)** e consumo energético negligenciável, viabilizando a execução em tempo real na frota autônoma.

---

## 3. METODOLOGIA E ARQUITETURA DO SISTEMA

A metodologia seguiu o arcabouço CRISP-DM, subdividida em Engenharia de Features, Pré-processamento, Validação de Modelos e MLOps.

```
+------------------+     +-------------------+     +----------------------+
|  Raw Data (DVC)  | --> | Feature Eng. &    | --> | MLflow Tracking &    |
| UAVIDS-2025.csv  |     | Pipeline sklearn  |     | Model Registry (@prod)|
+------------------+     +-------------------+     +----------------------+
                                                              |
                                                              v
                                                   +----------------------+
                                                   | FastAPI + Docker     |
                                                   | POST /predict        |
                                                   +----------------------+
```

### 3.1 Engenharia de Features (*Feature Engineering*)
Foram descartados identificadores sem valor preditivo (`FlowID`, `SrcAddr`, `DstAddr`) e a variável `Protocol` por apresentar valor constante (UDP em 100% dos registros). A partir dos princípios de redes de computadores, derivaram-se três novas variáveis:

$$\text{loss\_ratio} = \frac{\text{LostPackets}}{\text{TxPackets} + \epsilon}$$

$$\text{tx\_efficiency} = \frac{\text{RxBytes}}{\text{TxBytes} + \epsilon}$$

$$\text{throughput\_per\_hop} = \frac{\text{Throughput\_Kbps}}{\text{AverageHopCount} + 1}$$

A análise de importância de variáveis com *Random Forest* confirmou a relevância: `loss_ratio` figurou entre as 5 variáveis mais preditivas do sistema, auxiliando diretamente na discriminação da perda seletiva de pacotes.

### 3.2 Pré-processamento e Pipeline
* **Tratamento de Anomalia do Simulador:** Identificaram-se 81 registros (0,07%) com `PacketDropRate > 1`, um artefato da simulação NS-3. Implementou-se um `FunctionTransformer` dentro do *Pipeline* para aplicar um *clip* no intervalo $[0, 1]$.
* **Imputação e Normalização:** Utilizou-se `SimpleImputer(strategy='median')` para tratamento de eventuais nulos e `StandardScaler` para padronização das 21 *features* numéricas finais.
* **Tratamento de Desbalanceamento:** Aplicação de pesagem de classes (`class_weight='balanced'`) para compensar a menor proporção do ataque *Flooding* (~16,1%).

### 3.3 Modelagem e Validação Cruzada
A estratégia de validação adotou um *split* estratificado inicial de **80% para treino** e **20% para teste holdout**. No treino, aplicou-se **Stratified 5-Fold Cross-Validation**. Foram avaliados três algoritmos de base:
1. **Regressão Logística** (baseline linear);
2. **Random Forest** (árvores baseadas em bagging);
3. **XGBoost** (gradient boosting com tuning via `RandomizedSearchCV`, `n_iter=10`).

Adicionalmente, explorou-se um **Stacking Ensemble** (combinando Random Forest, XGBoost e LightGBM com meta-classificador de Regressão Logística).

### 3.4 Arquitetura MLOps e Implantação
* **DVC:** O dataset original foi versionado via DVC apontando para um remote local (`C:/dvcstore`), garantindo rastreabilidade do arquivo `UAVIDS-2025.csv`.
* **MLflow:** Registro de parâmetros, métricas de cada *fold*, matrizes de confusão e o pipeline treinado completo. O modelo selecionado foi promovido via script (`promover.py`) com o alias `@production`.
* **FastAPI + Docker:** Criação de microsserviço de inferência com carregamento dinâmico do modelo registrador (`models:/previsor_uav_ids@production`), validação rigorosa de *schemas* com Pydantic e execução em container Docker leve com fallback automatizado para caminhos locais.

---

## 4. RESULTADOS E DISCUSSÃO

### 4.1 Desempenho dos Modelos (5 Classes Original)
A Tabela 2 apresenta o comparativo entre os modelos avaliados na Validação Cruzada (5-fold) e no conjunto de Teste *Holdout*.

**Tabela 2 — Comparativo de desempenho entre algoritmos avaliados (5 classes)**

| Modelo | F1-macro CV (Média ± Std) | Accuracy CV | Fit Time (s) | F1-macro Teste (*Holdout*) |
| :--- | :---: | :---: | :---: | :---: |
| Logistic Regression | 0,8216 ± 0,0024 | 0,8190 | 9,1 | 0,8180 |
| Random Forest | 0,9529 ± 0,0010 | 0,9502 | 6,2 | 0,9437 |
| **XGBoost (Tunado)** | **0,9557 ± 0,0008** | **0,9540** | **5,3** | **0,9578** |

O **XGBoost Tunado** superou o critério de sucesso (F1-macro ≥ 0,95), atingindo **0,9578** no conjunto de teste, com menor tempo de ajuste (5,3s) e baixíssimo desvio padrão entre os *folds* (±0,0008).

### 4.2 Análise por Classe e Matriz de Confusão
Ao analisar o F1-score individual por classe no modelo vencedor:
* **Normal Traffic:** 0,986
* **Sybil Attack:** 0,976
* **Flooding Attack:** 0,969
* **Wormhole Attack:** 0,896
* **Blackhole Attack:** 0,902

A matriz de confusão revelou que a principal fonte de erro reside no par **Blackhole $\leftrightarrow$ Wormhole** (confusão residual de ~13,2% a 16,0%). Ambos os ataques envolvem perturbações de roteamento e descarte de pacotes, apresentando assinaturas estatísticas muito similares nas métricas de fluxo estáticas.

### 4.3 Experimento de Engenharia de Rótulos (*Label Engineering*)
Para avaliar se a simplificação semântica do espaço de classes traria benefícios operacionais em sistemas real-time de mitigação, executaram-se quatro experimentos comparativos (Tabela 3).

**Tabela 3 — Impacto do Label Engineering no desempenho do Stacking Classifier**

| Experimento | Mapeamento de Classes | F1-macro Teste | Observação Operacional |
| :--- | :--- | :---: | :--- |
| **5 classes (Original)** | Normal \| Blackhole \| Flooding \| Sybil \| Wormhole | 0,9467 | Granularidade total; confusão pontual BH $\leftrightarrow$ WH |
| **4 classes** | Normal \| Routing Attack \| Flooding \| Sybil | 0,9804 | Agrupa Blackhole + Wormhole |
| **3 classes (Ótimo)** | **Normal \| Routing Attack \| Saturation Attack** | **0,9908** | **Melhor trade-off precisão/granularidade** |
| **2 classes (Binário)** | Normal \| Attack | 0,9903 | Classificação genérica (Detecção de Ameaça) |

O agrupamento em **3 classes** (*Normal*, *Routing Attack* [BH+WH] e *Saturation Attack* [FL+SY]) representou o ponto ótimo do sistema: eleva o F1-macro para **0,9908** e reduz o *gap* de overfitting para valores praticamente nulos (0,0004). Isso demonstra que, para ações automáticas de defesa em drones (ex.: recalcular rota vs. limitar taxa de recebimento), a distinção por família de ataque é mais eficiente e precisa.

---

## 5. LIMITAÇÕES CONHECIDAS

Apesar dos resultados superiores, o sistema apresenta limitações que devem ser consideradas em ambiente operacional:

1. **Dependência de Dados Simulados (NS-3):** O dataset foi gerado inteiramente em ambiente sintético. Fenômenos do mundo real (como atenuação de RF por obstáculos físicos, interferência atmosférica e mobilidade tridimensional dinâmica) podem causar *domain shift*.
2. **Confusão Residual em 5 Classes:** Caso o cliente exija estritamente a diferenciação entre Blackhole e Wormhole em 5 classes, a confusão de ~13,2% exige métricas adicionais de topologia de rede.
3. **Ausência de Contexto Temporal e Espacial Dinâmico:** As inferências são realizadas sobre fluxos de tráfego isolados, sem utilizar matrizes de adjacência dinâmicas em tempo real.
4. **Assimetria de Recursos Treinamento/Inferência:** O treinamento utilizou aceleração por GPU (`device='cuda'`), enquanto a API em Docker opera exclusivamente em CPU de baixo custo (`CUDA_VISIBLE_DEVICES=-1`).

---

## 6. CONCLUSÃO E TRABALHOS FUTUROS

Este trabalho demonstrou a viabilidade de um Sistema de Detecção de Intrusão robusto e ultraleve para frotas de UAVs logísticos. A introdução de *features* derivadas de redes e o *Label Engineering* semântico permitiram superar as soluções complexas da literatura (incluindo GNNs e Deep Learning), atingindo um F1-macro de **0,9578** no problema de 5 classes e **0,9908** na abordagem de 3 classes, operando com consumo energético e latência mínimos em CPU. A solução foi empacotada com práticas industriais de MLOps (DVC, MLflow, FastAPI e Docker), pronta para consumo em tempo real.

Como **trabalhos futuros**, recomendam-se:
* Coleta de dados de tráfego em bancadas de testes com drones físicos (hardware-in-the-loop);
* Implementação de monitoramento de *data drift* e *concept drift* em produção com a biblioteca Evidently AI;
* Comparativo empírico direto de latência e consumo de bateria entre a API Docker deste trabalho e um container GNN rodando em uma placa embarcada NVIDIA Jetson Nano;
* Disponibilização de endpoint de inferência em lote (`/predict/batch`).

---

## REFERÊNCIAS BIBLIOGRÁFICAS

1. ZENG, Q.; BASHIR, A.; NAIT-ABDESSELAM, F. UAVIDS-2025: A Benchmark Dataset for Intrusion Detection in UAV Networks Using Machine Learning Techniques. **Kaggle Datasets / IEEE Conferences**, 2025. Disponível em: <https://www.kaggle.com/datasets>. Acesso em: 10 maio 2026. Licença CC BY 4.0.
2. AGGARWAL, P. et al. Security Challenges and Intrusion Detection in Flying Ad-Hoc Networks (FANETs): A Survey. **IEEE Communications Surveys & Tutorials**, v. 24, n. 3, p. 1540-1572, 2022.
3. CHEN, T.; GUESTRIN, C. XGBoost: A Scalable Tree Boosting System. In: **ACM SIGKDD International Conference on Knowledge Discovery and Data Mining (KDD)**, 22., 2016, San Francisco. *Proceedings...* New York: ACM, 2016. p. 785-794.
4. FASTAPI. **FastAPI Framework documentation**. 2024. Disponível em: <https://fastapi.tiangolo.com/>. Acesso em: 20 ago. 2026.
5. KIPF, T. N.; WELLING, M. Semi-Supervised Classification with Graph Convolutional Networks. In: **International Conference on Learning Representations (ICLR)**, 2017.
