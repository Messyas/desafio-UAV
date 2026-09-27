"""Create a local reproducibility bundle; no upload and no redistribution of raw data."""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.uavids_study.feature_ablation import job_grid, job_id, verified_records
from src.uavids_study.predictive_experiment import file_hash, json_hash, write_json


def package(config_path):
    config_path = Path(config_path).resolve()
    config = json.loads(config_path.read_text("utf-8"))
    results = ROOT / "results" / config["experiment_id"]
    report = ROOT / "reports" / config["experiment_id"]
    analysis = json.loads((report / "analysis_manifest.json").read_text("utf-8"))
    frozen = json.loads((results / "frozen_protocol.json").read_text("utf-8"))
    if analysis["config_sha256"] != json_hash(config) or frozen["config"] != config:
        raise ValueError("Package configuration differs from the experiment")
    if not analysis["requested_protocols_complete"]:
        raise ValueError("Requested analysis is incomplete")
    analysis_code_name = "sensitivity_analysis.py" if "reference_experiment" in analysis else "paired_analysis.py"
    if file_hash(ROOT / "src/uavids_study" / analysis_code_name) != analysis["analysis_code_sha256"]:
        raise ValueError("Analysis code changed after the saved report")
    all_records = verified_records(results, config)
    records = [record for record in all_records if record["protocol"] in analysis["protocols"]]
    current_manifest = json.loads((results / "experiment_manifest.json").read_text("utf-8"))
    if current_manifest["completed_jobs"] != len(all_records):
        raise ValueError("Experiment manifest is stale; aggregate before packaging")
    expected = {job_id(cell) for cell in job_grid(config) if cell[0] in analysis["protocols"]}
    if {record["job_id"] for record in records} != expected:
        raise ValueError("Requested protocol coverage is incomplete")
    identities = {item["job_id"]: item["prediction_sha256"] for item in analysis["prediction_inputs"]}
    if identities != {record["job_id"]: record["prediction_sha256"] for record in records}:
        raise ValueError("Analysis predictions differ from the current artifacts")
    for name, checksum in frozen["identity"]["code_sha256"].items():
        if file_hash(ROOT / "src/uavids_study" / name) != checksum:
            raise ValueError("Training code changed after execution")
    split_path = ROOT / config.get("split_path", "research_artifacts/data_audit/split_candidates.csv.gz")
    if file_hash(split_path) != frozen["identity"]["split_sha256"]:
        raise ValueError("Partitions changed after execution")
    for name, checksum in analysis["output_sha256"].items():
        path = (report / name).resolve()
        if not path.is_relative_to(report.resolve()) or file_hash(path) != checksum:
            raise ValueError("Analysis tables changed after verification")
    files = {config_path, split_path, report / "analysis_manifest.json",
        results / "frozen_protocol.json", results / "experiment_manifest.json", results / "fold_metrics.csv"}
    files.update(report / name for name in analysis["output_sha256"])
    parity_path = report / "control_parity_manifest.json"
    if parity_path.exists():
        parity = json.loads(parity_path.read_text("utf-8"))
        parity_table = report / "control_parity.csv"
        if parity["new_config_sha256"] != json_hash(config) or file_hash(parity_table) != parity["table_sha256"]:
            raise ValueError("Control parity report changed")
        files.update((parity_path, parity_table))
    for record in all_records:
        files.update((results / record["prediction_file"], results / "job_records" / (record["job_id"] + ".json")))
    if "reference_experiment" in analysis:
        reference_name = analysis["reference_experiment"]
        reference_config_path = ROOT / "configs" / (reference_name + ".json")
        reference_config = json.loads(reference_config_path.read_text("utf-8"))
        reference_output = ROOT / "results" / reference_name
        reference_frozen = json.loads((reference_output / "frozen_protocol.json").read_text("utf-8"))
        if (json_hash(reference_config) != analysis["reference_config_sha256"] or
            reference_frozen["identity"]["dataset_sha256"] != frozen["identity"]["dataset_sha256"] or
            reference_frozen["identity"]["split_sha256"] != frozen["identity"]["split_sha256"] or
            reference_frozen["identity"]["code_sha256"] != frozen["identity"]["code_sha256"] or
            reference_frozen["identity"]["environment"] != frozen["identity"]["environment"]):
            raise ValueError("Reference experiment differs from paired sensitivity")
        reference_records = {record["job_id"]: record for record in verified_records(reference_output, reference_config)}
        for item in analysis["reference_predictions"]:
            reference_record = reference_records[item["job_id"]]
            if reference_record["prediction_sha256"] != item["prediction_sha256"]:
                raise ValueError("Reference prediction changed")
            files.update((reference_output / reference_record["prediction_file"],
                reference_output / "job_records" / (item["job_id"] + ".json")))
        files.update((reference_config_path, reference_output / "frozen_protocol.json",
            reference_output / "experiment_manifest.json"))
        files.add(report / "sensitivity_manifest.json")
    for folder in ("src/uavids_study", "protocol", "provenance", "tests"):
        files.update(path for path in (ROOT / folder).rglob("*") if path.is_file() and path.suffix in {".py", ".md", ".json"})
    files.update((ROOT / "tools").glob("*.py"))
    files.update((ROOT / "research_artifacts/data_audit").glob("*.csv"))
    files.add(ROOT / "research_artifacts/data_audit/data_manifest.json")
    files.update((ROOT / "research_artifacts/derived_features").glob("*.json"))
    files.update((ROOT / "research_artifacts/derived_features").glob("*.csv"))
    for name in ("requirements-research.txt", "requirements-tracking.txt", "README.md", "RESEARCH_WORKFLOW.md", "PLANO_CIENTIFICO_UAVIDS2025.md"):
        files.add(ROOT / name)
    # Reference configs are needed to verify the baseline identity in a clean clone.
    files.update((ROOT / "configs").glob("*.json"))
    for manifest_name in ("report_manifest.json",):
        path = report / manifest_name
        if path.exists():
            rendered = json.loads(path.read_text("utf-8"))
            if rendered["analysis_manifest_sha256"] != file_hash(report / "analysis_manifest.json"):
                raise ValueError("Figure report belongs to another analysis")
            for name, checksum in rendered["output_sha256"].items():
                artifact = (report / name).resolve()
                if not artifact.is_relative_to(report.resolve()) or file_hash(artifact) != checksum:
                    raise ValueError("Rendered report artifact changed")
                files.add(artifact)
            files.add(path)
    for path in files:
        if not path.resolve().is_relative_to(ROOT.resolve()) or not path.is_file():
            raise ValueError(f"Invalid bundle path: {path}")
    entries = {path.relative_to(ROOT).as_posix(): file_hash(path) for path in sorted(files)}
    manifest = {"experiment_id": config["experiment_id"], "protocols": analysis["protocols"],
        "whole_experiment_complete": current_manifest["complete"],
        "included_prediction_jobs": len(all_records),
        "analysis_snapshot_whole_experiment_complete": analysis["whole_experiment_complete"],
        "dataset_sha256": frozen["identity"]["dataset_sha256"],
        "raw_data_included": False, "files_sha256": entries,
        "reference_experiment": analysis.get("reference_experiment"),
        "limits": "Local bundle only. Obtain canonical data via tools/fetch_dataset.py; review licenses before public deposit."}
    destination = ROOT / "research_artifacts/releases"
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / (config["experiment_id"] + "__" + "_".join(analysis["protocols"]) + ".zip")
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in entries:
            archive.write(ROOT / name, name)
        archive.writestr("BUNDLE_MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    write_json(path.with_suffix(".manifest.json"), {**manifest, "zip_sha256": file_hash(path)})
    print(path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "configs/feature_ablation_v4.json")
    package(parser.parse_args().config)
