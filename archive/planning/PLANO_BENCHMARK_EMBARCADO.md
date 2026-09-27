# PLANO DE EXPANSÃO DE PESQUISA: BENCHMARK DE LATÊNCIA E RECURSOS EM AMBIENTE EMBARCADO (EDGE UAV)

Este documento registra o planejamento das melhorias e experimentos propostos para elevar o artigo ao **estado da arte científico e de engenharia**, comprovando empiricamente a eficiência do modelo leve em hardware restrito.

---

## 1. OBJETIVO DOS NOVOS EXPERIMENTOS

Validar e quantificar o *trade-off* entre **Acurácia (F1-score)**, **Latência de Inferência (P50, P90, P99)** e **Consumo de Recursos (CPU/RAM)** ao executar a detecção de intrusão em um ambiente Docker que simula um microprocessador de drone (ex.: Raspberry Pi 4 / NVIDIA Jetson Nano em modo de economia).

---

## 2. RESTRIÇÃO DE RECURSOS NO DOCKER (SIMULAÇÃO DE EDGE COMPUTING)

Para simular o hardware embarcado do drone, os containers de inferência serão executados com cláusulas rígidas de limitação de recursos via `docker run` ou `docker-compose.yml` utilizando cgroups:

```yaml
services:
  uav-ids-api:
    build: .
    ports:
      - "8000:8000"
    deploy:
      resources:
        limits:
          cpus: '0.50'      # Máximo de 50% de 1 vCPU (Simula processador leve de drone)
          memory: 512M      # Máximo de 512 MB de RAM
        reservations:
          cpus: '0.25'
          memory: 256M
```

Via linha de comando Docker CLI:
```bash
docker run -d -p 8000:8000 --cpus="0.5" --memory="512m" --name ids-uav-edge uavids-api:latest
```

---

## 3. PROTOCOLO DE MEDIÇÃO DE LATÊNCIA E PERFORMANCE (SLA DE PRODUÇÃO)

Será executado um teste de carga utilizando scripts assíncronos (`httpx` + `asyncio`) ou **Locust** para simular o recebimento contínuo de fluxos de rede em tempo real.

### Métricas a Coletar:
* **Latência Média & Mediana (P50):** Tempo médio de resposta do endpoint `/predict`.
* **Latência de Cauda (P90 e P99):** Garantia de SLA para os 10% e 1% de requisições mais lentas (crítico para sistemas de voo autônomo em tempo real).
* **Throughput (RPS):** Quantidade de requisições processadas por segundo (`Requests Per Second`).
* **Footprint de Memória (RAM em MB):** Uso de memória do container em repouso e sob pico de carga.
* **Uso de CPU (%):** Taxa de ocupação dos núcleos limitados.

---

## 4. BASELINE DE MODELO DE GRAFOS (GNN) PARA COMPARAÇÃO EMPÍRICA

Para realizar o confronto direto com a literatura recente de GNNs no dataset UAVIDS-2025, será desenvolvida uma implementação baseline em **PyTorch Geometric (PyG)**:

* **Arquitetura:** Graph Attention Network (GAT) ou Relational Graph Convolutional Network (R-GCN).
* **Estrutura de Dados:** Grafo montado a partir de `SrcAddr` e `DstAddr` com os atributos numéricos das arestas.
* **Overhead a Medir:** 
  1. Tempo de montagem da matriz de adjacência do grafo dinâmico.
  2. Tempo de inferência do modelo GNN na CPU limitada.
  3. Consumo de memória RAM do PyTorch/PyG no container.

---

## 5. TABELA DE RESULTADOS ESPERADOS DO BENCHMARK

A tabela final a ser incorporada na versão expandida do artigo científico seguirá este modelo:

| Modelo / Abordagem | Limite de Hardware (Docker) | F1-Score | Latência P50 (ms) | Latência P90 (ms) | Latência P99 (ms) | Throughput (RPS) | Uso de RAM (MB) |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **GNN (PyTorch Geometric - GAT)** | 0.5 CPU / 512MB RAM | ~0.975 | ~35.0 ms | ~65.0 ms | ~110.0 ms | ~28 req/s | ~420 MB |
| **XGBoost Tunado (5 classes)** | 0.5 CPU / 512MB RAM | 0.9578 | ~1.2 ms | ~2.5 ms | ~4.8 ms | ~450 req/s | ~110 MB |
| **Stacking Tunado (3 classes)** | 0.5 CPU / 512MB RAM | **0.9908** | **~1.8 ms** | **~3.2 ms** | **~5.9 ms** | **~380 req/s** | **~140 MB** |

---

## 6. PRÓXIMOS PASSOS DE EXECUÇÃO

1. [ ] Atualizar o `docker-compose.yml` adicionando a cláusula `resources.limits` (0.5 CPUs, 512MB RAM).
2. [ ] Criar script de teste de latência em Python (`locustfile.py` ou `test_latencia.py` com `httpx`).
3. [ ] Medir P50, P90, P99 e RPS no container do XGBoost / Stacking atual.
4. [ ] Desenvolver protótipo baseline em PyTorch Geometric para extrair métricas comparativas da GNN.
5. [ ] Atualizar o artigo com a seção dedicada ao Benchmark de Latência e Recursos Embarcados.
