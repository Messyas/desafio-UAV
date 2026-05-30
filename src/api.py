import logging, os
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlparse
import mlflow
import mlflow.pyfunc
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from mlflow.tracking import MlflowClient

MLFLOW_URI    = os.getenv("MLFLOW_TRACKING_URI", "file:./notebooks/mlruns")
MODEL_REG     = "previsor_uav_ids"
MODEL_ALIAS   = "production"
MODEL_NAME    = f"models:/{MODEL_REG}@{MODEL_ALIAS}"
EPS_SMALL     = 1e-9
EPS_HOP       = 1.0

# Fallback caso o modelo retorne inteiros (LabelEncoder do XGBoost).
# O RandomForest tunado retorna direto o nome da classe (string).
LABEL_MAP = {
    0: "Blackhole Attack",
    1: "Flooding Attack",
    2: "Normal Traffic",
    3: "Sybil Attack",
    4: "Wormhole Attack",
}

mlflow.set_tracking_uri(MLFLOW_URI)
model = None


def carregar_modelo_producao():
    """Carrega o modelo @production de forma portavel.

    Tenta a URI do registry (models:/nome@alias). Se o storage_location
    gravado for um caminho absoluto que nao existe no ambiente atual
    (tipico ao rodar dentro de um container, pois o caminho foi salvo
    no host), reescreve o caminho para o mlruns montado localmente.
    """
    try:
        return mlflow.pyfunc.load_model(MODEL_NAME)
    except Exception as exc_uri:
        logger.warning(f"Load via URI do registry falhou ({exc_uri}); tentando caminho local.")
        client = MlflowClient()
        mv = client.get_model_version_by_alias(MODEL_REG, MODEL_ALIAS)
        root = Path(os.path.abspath(MLFLOW_URI.replace("file:", "")))
        meta_path = root / "models" / MODEL_REG / f"version-{mv.version}" / "meta.yaml"
        if not meta_path.exists():
            raise exc_uri

        storage_location = ""
        for line in meta_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("storage_location:"):
                storage_location = line.split(":", 1)[1].strip().strip("'\"")
                break

        if not storage_location:
            raise exc_uri

        parsed = urlparse(storage_location)
        storage_path = parsed.path if parsed.scheme == "file" else storage_location
        marker = "/notebooks/mlruns/"
        if marker in storage_path:
            rel = storage_path.split(marker, 1)[1]
            local_path = root / rel
        else:
            local_path = Path(storage_path)

        logger.info(f"Carregando modelo via caminho local: {local_path}")
        return mlflow.pyfunc.load_model(str(local_path))


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    try:
        logger.info(f"Carregando modelo: {MODEL_NAME}")
        model = carregar_modelo_producao()
        logger.info("Modelo carregado e pronto.")
    except Exception as exc:
        logger.error(f"Falha ao carregar modelo: {exc}")
        model = None
    yield
    model = None


app = FastAPI(
    title="UAVIDS-2025 - IDS para Redes UAV",
    description="Classifica fluxos de rede de drones. Modelo: RandomForest tunado - F1-macro ~ 0,946.",
    version="1.0.0",
    lifespan=lifespan,
)


class TrafficFeatures(BaseModel):
    FlowDuration_s:  float = Field(..., example=0.123456, description="FlowDuration/s")
    SrcPort:         int   = Field(..., example=49152)
    DstPort:         int   = Field(..., example=80)
    TxPackets:       int   = Field(..., example=10)
    RxPackets:       int   = Field(..., example=8)
    LostPackets:     int   = Field(..., example=0)
    TxBytes:         int   = Field(..., example=1400)
    RxBytes:         int   = Field(..., example=1120)
    TxPacketRate_s:  float = Field(..., example=5.0,   description="TxPacketRate/s")
    RxPacketRate_s:  float = Field(..., example=4.0,   description="RxPacketRate/s")
    TxByteRate_s:    float = Field(..., example=700.0, description="TxByteRate/s")
    RxByteRate_s:    float = Field(..., example=560.0, description="RxByteRate/s")
    MeanPacketSize:  float = Field(..., example=140.0)
    MeanDelay_s:     float = Field(..., example=0.002,  description="MeanDelay/s")
    MeanJitter_s:    float = Field(..., example=0.0001, description="MeanJitter/s")
    Throughput_Kbps: float = Field(..., example=5.6,    description="Throughput/Kbps")
    PacketDropRate:  float = Field(..., example=0.0)
    AverageHopCount: float = Field(..., example=3.0)


class PredictionResponse(BaseModel):
    predicao: str
    modelo:   str


def build_df(f: TrafficFeatures) -> pd.DataFrame:
    return pd.DataFrame([{
        "FlowDuration/s":     f.FlowDuration_s,
        "SrcPort":            f.SrcPort,
        "DstPort":            f.DstPort,
        "TxPackets":          f.TxPackets,
        "RxPackets":          f.RxPackets,
        "LostPackets":        f.LostPackets,
        "TxBytes":            f.TxBytes,
        "RxBytes":            f.RxBytes,
        "TxPacketRate/s":     f.TxPacketRate_s,
        "RxPacketRate/s":     f.RxPacketRate_s,
        "TxByteRate/s":       f.TxByteRate_s,
        "RxByteRate/s":       f.RxByteRate_s,
        "MeanPacketSize":     f.MeanPacketSize,
        "MeanDelay/s":        f.MeanDelay_s,
        "MeanJitter/s":       f.MeanJitter_s,
        "Throughput/Kbps":    f.Throughput_Kbps,
        "PacketDropRate":     f.PacketDropRate,
        "AverageHopCount":    f.AverageHopCount,
        "loss_ratio":         f.LostPackets     / (f.TxPackets       + EPS_SMALL),
        "tx_efficiency":      f.RxBytes         / (f.TxBytes         + EPS_SMALL),
        "throughput_per_hop": f.Throughput_Kbps / (f.AverageHopCount + EPS_HOP),
    }])


@app.get("/saude")
def saude():
    if model is None:
        raise HTTPException(status_code=500, detail="Modelo nao carregado.")
    return {"ok": True, "modelo": MODEL_NAME}


@app.post("/predict", response_model=PredictionResponse)
def predict(features: TrafficFeatures):
    if model is None:
        raise HTTPException(status_code=503, detail="Modelo nao disponivel.")
    try:
        raw = model.predict(build_df(features))[0]
        # RandomForest retorna string ("Blackhole Attack"); XGBoost retorna int (0..4).
        try:
            label = LABEL_MAP.get(int(raw), str(raw))
        except (ValueError, TypeError):
            label = str(raw)
        return PredictionResponse(predicao=label, modelo=MODEL_NAME)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
