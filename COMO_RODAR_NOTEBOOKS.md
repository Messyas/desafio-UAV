# Como rodar os notebooks no container NVIDIA

## Pré-requisito
A imagem `nvcr.io/nvidia/pytorch:24.03-py3` já deve estar baixada localmente.

---

## 1. Subir o container com Jupyter

```bash
docker run --gpus all -it --rm \
  -v "C:/Users/User/Documents/datasci:/workspace" \
  -w /workspace \
  -p 8888:8888 \
  -p 5002:5002 \
  -e MLFLOW_TRACKING_URI=sqlite:////workspace/mlruns/mlflow.db \
  nvcr.io/nvidia/pytorch:24.03-py3 \
  jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --NotebookApp.token=''
```

> **Windows PowerShell:** substitua as `\` por `` ` `` para quebrar linhas, ou cole tudo em uma linha só.

---

## 2. Acessar o Jupyter

Abra o browser em: **http://localhost:8888**

Os notebooks estão em `notebooks/`.

---

## 3. Subir a MLflow UI (opcional, em outro terminal)

Com o container rodando, abra outro terminal e execute:

```bash
docker run --rm \
  -v "C:/Users/User/Documents/datasci:/workspace" \
  -w /workspace \
  -p 5002:5002 \
  -e MLFLOW_TRACKING_URI=sqlite:////workspace/mlruns/mlflow.db \
  nvcr.io/nvidia/pytorch:24.03-py3 \
  mlflow ui --backend-store-uri sqlite:////workspace/mlruns/mlflow.db --host 0.0.0.0 --port 5002
```

Acesse em: **http://localhost:5002**

---

## Observações

- O dataset deve estar em `data/raw/UAVIDS-2025.csv` (restaurado via `dvc pull` se necessário)
- O `MLFLOW_TRACKING_URI` já está configurado na célula 0 de `02_modelagem.ipynb` — não precisa mudar nada
- Os notebooks já têm todos os outputs salvos; só re-execute se quiser re-treinar
- Para parar o container: `Ctrl+C` no terminal onde ele está rodando
