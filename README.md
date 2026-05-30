# UAVIDS-2025 — Detecção de Intrusão em Redes UAV

## Descrição do Problema

Redes de drones (UAV) são vulneráveis a ataques como Blackhole, Flooding, Sybil e Wormhole. Este projeto treina um classificador capaz de identificar o tipo de tráfego de rede a partir de métricas de fluxo, servindo como um **Sistema de Detecção de Intrusão (IDS)** para frotas de drones.

**Cliente fictício:** equipe de segurança de uma empresa de logística com drones autônomos.  
**Métrica de sucesso:** F1-macro ≥ 0,95 no conjunto de teste holdout (alcançado: **0,9578**).

---

## Origem do Dataset

| Campo | Valor |
|---|---|
| Nome | UAVIDS-2025 |
| Fonte | Kaggle — [UAVIDS-2025 Dataset](https://www.kaggle.com/datasets) |
| Data de download | 10/05/2026 |
| Licença | CC BY 4.0 |
| Tamanho | 122.171 instâncias × 23 colunas |
| Problema | Classificação multiclasse (5 classes) |

---

## Pré-requisitos

- Docker Desktop (com Docker Compose)
- Git
- Python 3.12 (para o ambiente local de notebooks)
- DVC (`pip install "dvc"`)

---

## Como Reproduzir (passo a passo)

### 1. Clonar o repositório

```bash
git clone <URL_DO_REPOSITORIO>
cd datasci
```

### 2. Restaurar o dataset via DVC

O dataset não está no Git — está versionado pelo DVC em um remote local.  
Inclua a pasta `C:/dvcstore` (entregue junto no `.zip`) na raiz do seu `C:/` e então execute:

```bash
dvc pull
```

> Isso restaura o arquivo `data/raw/UAVIDS-2025.csv` a partir do remote local `C:/dvcstore`.

### 3. Criar o ambiente local (notebooks)

O projeto usa um `.venv` Python 3.12 com todas as dependências para rodar os notebooks. Caso o `.venv` não exista (clone limpo), crie com:

```powershell
py -3.12 -m venv .venv
.venv\Scripts\pip install -r requirements-notebooks.txt
```

### 4. Abrir os notebooks no VS Code

1. Abrir a pasta do projeto no VS Code
2. Instalar a extensão **Jupyter** (Microsoft) se ainda não tiver
3. Abrir `notebooks/01_eda.ipynb` ou `notebooks/02_modelagem.ipynb`
4. No canto superior direito do notebook, clicar em **Select Kernel** → **Python Environments** → escolher o interpretador `.venv\Scripts\python.exe`
5. Rodar as células normalmente (Shift+Enter ou `Run All`)

Ordem sugerida:

```
notebooks/01_eda.ipynb       # EDA detalhada
notebooks/02_modelagem.ipynb # Pipeline, CV, MLflow, Registry
```

> Os artefatos do MLflow (`notebooks/mlruns/`) já estão incluídos com os modelos treinados e o alias `@production` configurado. Só re-execute se quiser re-treinar.

### 5. Promover o modelo para @production (já feito, opcional re-executar)

```bash
python src/promover.py
```

> Atribui o alias `@production` à versão 4 do modelo `previsor_uav_ids` no MLflow Registry.

### 6. Subir a API com Docker Compose

```bash
docker compose up --build
```

A API sobe na porta **8000**. Aguarde a mensagem `Modelo carregado e pronto.` nos logs.

### 7. Testar os endpoints

```bash
# Health check
curl http://localhost:8000/saude

# Predição
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "FlowDuration_s": 0.123456,
    "SrcPort": 49152,
    "DstPort": 80,
    "TxPackets": 10,
    "RxPackets": 8,
    "LostPackets": 0,
    "TxBytes": 1400,
    "RxBytes": 1120,
    "TxPacketRate_s": 5.0,
    "RxPacketRate_s": 4.0,
    "TxByteRate_s": 700.0,
    "RxByteRate_s": 560.0,
    "MeanPacketSize": 140.0,
    "MeanDelay_s": 0.002,
    "MeanJitter_s": 0.0001,
    "Throughput_Kbps": 5.6,
    "PacketDropRate": 0.0,
    "AverageHopCount": 3.0
  }'
```

Documentação interativa (Swagger): **http://localhost:8000/docs**

### 8. Visualizar o MLflow UI

```bash
mlflow ui --backend-store-uri file:./notebooks/mlruns --port 5002
```

Acesse: **http://localhost:5002**

---

## Comparativo dos 3 Modelos

| Modelo | F1-macro CV (média) | F1-macro CV (std) | Accuracy CV | Fit time (s) |
|---|---|---|---|---|
| LogisticRegression | 0,8216 | ±0,0024 | 0,8190 | 9,1 |
| RandomForest | 0,9529 | ±0,0010 | 0,9502 | 6,2 |
| **XGBoost (vencedor)** | **0,9564** | **±0,0008** | **0,9540** | **5,3** |

**XGBoost tunado (RandomizedSearchCV, n_iter=10, cv=5):**

| Métrica | Valor |
|---|---|
| F1-macro CV (pós-tuning) | 0,9557 |
| F1-macro Teste (holdout 20%) | **0,9578** |
| Accuracy Teste | 0,9554 |

---

## Decisões de Modelagem

**Features removidas:**
- `FlowID`, `SrcAddr`, `DstAddr` — identificadores sem valor preditivo
- `Protocol` — constante em todo o dataset (valor único: UDP)

**Feature engineering (3 features derivadas):**
- `loss_ratio = LostPackets / TxPackets` — taxa de perda de pacotes
- `tx_efficiency = RxBytes / TxBytes` — eficiência de transmissão
- `throughput_per_hop = Throughput/Kbps / AverageHopCount` — throughput normalizado por salto

**Pré-processamento (dentro do Pipeline, sem data leakage):**
- `FunctionTransformer` — clip de `PacketDropRate` para [0, 1] (81 registros com valor > 1)
- `SimpleImputer(strategy='median')` — imputação de valores ausentes
- `StandardScaler` — normalização de todas as 21 features numéricas
- Não há features categóricas (Protocol era constante e foi removida)

**Balanceamento:** `class_weight='balanced'` em todos os modelos (Flooding Attack com 16,1% do dataset)

**Validação:** Stratified 5-Fold, split 80/20 estratificado antes de qualquer ajuste

---

## Limitações Conhecidas e Próximos Passos

**Limitações:**
- Modelo treinado em ambiente simulado (NS-3) — pode ter gap de desempenho em tráfego real
- Confusão residual entre Blackhole ↔ Wormhole: 13,2% (artigo original reporta 10–15% com ensembles)
- `device='cuda'` no treinamento — container de produção usa CPU via `CUDA_VISIBLE_DEVICES=-1`

**Próximos passos:**
- Coletar dados de redes UAV reais para re-treinar
- Adicionar monitoramento de drift com Evidently AI
- Explorar LightGBM e modelos de grafos para capturar topologia da rede
- Implementar endpoint `/predict/batch` para inferência em lote
