import logging, os
from contextlib import asynccontextmanager
import mlflow
import mlflow.pyfunc
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MLFLOW_URI = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
MODEL_NAME = "models:/previsor_uav_ids@production"
EPS_SMALL  = 1e-9
EPS_HOP    = 1.0

# XGBoost foi treinado com LabelEncoder - mapeia inteiros para nomes das classes
LABEL_MAP = {
    0: "Blackhole Attack",
    1: "Flooding Attack",
    2: "Normal Traffic",
    3: "Sybil Attack",
    4: "Wormhole Attack",
}

mlflow.set_tracking_uri(MLFLOW_URI)
model = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model
    try:
        logger.info(f"Carregando modelo via pyfunc: {MODEL_NAME}")
        model = mlflow.pyfunc.load_model(MODEL_NAME)
        logger.info("Modelo carregado e pronto.")
    except Exception as exc:
        logger.error(f"Falha ao carregar modelo: {exc}")
        model = None
    yield
    model = None


app = FastAPI(
    title="UAVIDS-2025 - IDS para Redes UAV",
    description="Classifica fluxos de rede de drones. Modelo: XGBoost tunado - F1-macro ~ 0,958.",
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
        label = LABEL_MAP.get(int(raw), str(raw))
        return PredictionResponse(predicao=label, modelo=MODEL_NAME)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
