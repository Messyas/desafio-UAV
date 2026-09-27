"""
Promove o modelo vencedor (XGBoost tunado) para o alias @production no MLflow Registry.
Uso: python src/promover.py [--version 4]
"""

import argparse
import os

import mlflow
from mlflow.tracking import MlflowClient

MODEL_NAME = "previsor_uav_ids"
ALIAS = "production"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version",
        type=str,
        default="4",
        help="Versão do modelo a promover (default: 4)",
    )
    args = parser.parse_args()

    uri = os.getenv("MLFLOW_TRACKING_URI", "file:./notebooks/mlruns")
    mlflow.set_tracking_uri(uri)
    client = MlflowClient()

    try:
        reg = client.get_registered_model(MODEL_NAME)
        print(f"Modelo encontrado: {reg.name}")
    except Exception as exc:
        print(f"ERRO: modelo '{MODEL_NAME}' não encontrado no Registry — {exc}")
        raise SystemExit(1)

    versions = client.search_model_versions(f"name='{MODEL_NAME}'")
    print(f"Versões disponíveis: {[v.version for v in versions]}")

    client.set_registered_model_alias(MODEL_NAME, ALIAS, args.version)

    mv = client.get_model_version_by_alias(MODEL_NAME, ALIAS)
    print(f"\nAlias @{ALIAS} -> versão {mv.version} (run_id={mv.run_id})")
    print(f"URI de produção: models:/{MODEL_NAME}@{ALIAS}")
    print("✓ Promoção concluída.")


if __name__ == "__main__":
    main()
