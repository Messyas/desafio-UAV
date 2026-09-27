"""Mirror saved experiment jobs into optional MLflow tracking, without training."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def prepare_export(result_dir: Path, config_path: Path) -> tuple[dict, list[dict]]:
    """Validate provenance and prediction integrity before opening any tracking run."""
    manifest = json.loads((result_dir / "experiment_manifest.json").read_text("utf-8"))
    config = json.loads(config_path.read_text("utf-8"))
    config_hash = hashlib.sha256(
        json.dumps(config, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if config_hash != manifest["config_sha256"]:
        raise ValueError("Configuration differs from the experiment manifest")
    if config["experiment_id"] != manifest["experiment_id"]:
        raise ValueError("Experiment identifiers differ")
    records = []
    for path in sorted((result_dir / "job_records").glob("*.json")):
        record = json.loads(path.read_text("utf-8"))
        if record.get("status") != "complete":
            continue
        if record.get("config_sha256") != config_hash:
            raise ValueError(f"Mixed configurations in {path}")
        prediction = (result_dir / record["prediction_file"]).resolve()
        if not prediction.is_relative_to(result_dir.resolve()):
            raise ValueError(f"Prediction path outside result directory: {prediction}")
        if file_hash(prediction) != record["prediction_sha256"]:
            raise ValueError(f"Prediction checksum mismatch: {prediction}")
        records.append({"record": record, "path": path, "prediction": prediction})
    if not records or len(records) != manifest["completed_jobs"]:
        raise ValueError("Completed job count differs from the manifest")
    return manifest, records


def export_mlflow(
    result_dir: Path, config_path: Path, *, tracking_uri: str | None = None,
    include_predictions: bool = False, max_jobs: int | None = None,
) -> dict:
    manifest, jobs = prepare_export(result_dir, config_path)
    config = json.loads(config_path.read_text("utf-8"))
    try:
        from mlflow.tracking import MlflowClient
    except ImportError as exc:
        raise RuntimeError("Install requirements-tracking.txt to enable MLflow") from exc
    tracking_dir = ROOT / "tracking"
    tracking_dir.mkdir(exist_ok=True)
    uri = tracking_uri or f"sqlite:///{(tracking_dir / 'mlflow.db').as_posix()}"
    client = MlflowClient(tracking_uri=uri)
    experiment_name = f"uavids/{manifest['experiment_id']}"
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        artifact_dir = tracking_dir / "artifacts" / manifest["experiment_id"]
        artifact_dir.mkdir(parents=True, exist_ok=True)
        experiment_id = client.create_experiment(
            experiment_name, artifact_location=artifact_dir.resolve().as_uri()
        )
    else:
        experiment_id = experiment.experiment_id
    exported = skipped = 0
    for item in jobs[:max_jobs]:
        record = item["record"]
        identity = {
            "export_schema": "1",
            "job_id": record["job_id"],
            "config_sha256": manifest["config_sha256"],
            "prediction_sha256": record["prediction_sha256"],
            "dataset_sha256": manifest["dataset_sha256"],
            "split_sha256": manifest["split_sha256"],
        }
        matching = client.search_runs(
            [experiment_id],
            filter_string=f"tags.job_id = '{record['job_id']}'",
        )
        if any(
            run.info.status == "FINISHED"
            and all(run.data.tags.get(key) == value for key, value in identity.items())
            and (not include_predictions or run.data.tags.get("includes_predictions") == "true")
            for run in matching
        ):
            for saved_run in matching:
                if saved_run.info.status == "FINISHED" and all(
                    saved_run.data.tags.get(key) == value for key, value in identity.items()
                ):
                    client.set_tag(saved_run.info.run_id, "experiment_complete", str(manifest["complete"]).lower())
            skipped += 1
            continue
        tags = {
            **identity, "mlflow.runName": record["job_id"],
            "scientific_status": manifest["status"],
            "experiment_complete": str(manifest["complete"]).lower(),
            "diagnostic_only": str(record.get("diagnostic_only", False)).lower(),
            "source": "saved_predictions_no_retraining",
            "includes_predictions": str(include_predictions).lower(),
        }
        run = client.create_run(experiment_id, tags=tags)
        run_id = run.info.run_id
        try:
            for key in ("protocol", "fold", "model", "seed"):
                client.log_param(run_id, key, record[key])
            if "condition" in record:
                client.log_param(run_id, "condition", record["condition"])
                client.log_param(run_id, "features", json.dumps(record["features"]))
                client.log_param(run_id, "clip_packet_drop_rate", record["clip_packet_drop_rate"])
            parameters = record.get(
                "selected_parameters", config["models"][record["model"]].get("parameters", {})
            )
            for key, value in parameters.items():
                client.log_param(run_id, f"model.{key}", value)
            for key, value in record["metrics"].items():
                if isinstance(value, (int, float)) and math.isfinite(value):
                    client.log_metric(run_id, key, value)
            for key in ("fit_seconds", "inference_seconds", "serialized_model_bytes"):
                value = record.get(key)
                if isinstance(value, (int, float)) and math.isfinite(value):
                    client.log_metric(run_id, key, value)
            for path in (config_path, result_dir / "experiment_manifest.json", item["path"]):
                client.log_artifact(run_id, str(path))
            frozen_path = result_dir / "frozen_protocol.json"
            if frozen_path.exists():
                client.log_artifact(run_id, str(frozen_path))
            if include_predictions:
                client.log_artifact(run_id, str(item["prediction"]), artifact_path="predictions")
            client.set_terminated(run_id, status="FINISHED")
        except Exception:
            client.set_terminated(run_id, status="FAILED")
            raise
        exported += 1
    return {"experiment": experiment_name, "exported": exported, "skipped": skipped}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true", help="Validate without importing MLflow")
    parser.add_argument("--include-predictions", action="store_true")
    parser.add_argument("--max-jobs", type=int)
    args = parser.parse_args()
    if args.max_jobs is not None and args.max_jobs < 1:
        parser.error("--max-jobs must be positive")
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text("utf-8"))
    result_dir = ROOT / "results" / config["experiment_id"]
    if args.dry_run:
        manifest, jobs = prepare_export(result_dir, config_path)
        result = {"experiment": manifest["experiment_id"], "verified_jobs": len(jobs)}
    else:
        result = export_mlflow(
            result_dir, config_path, include_predictions=args.include_predictions,
            max_jobs=args.max_jobs,
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
