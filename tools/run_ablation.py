"""Run the frozen ablation CLI and retain failed invocation diagnostics locally."""
from __future__ import annotations

import json
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.uavids_study.feature_ablation import main
from src.uavids_study.predictive_experiment import json_hash, write_json


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        config_path = ROOT / "configs/feature_ablation_v4.json"
        if "--config" in sys.argv:
            index = sys.argv.index("--config") + 1
            if index < len(sys.argv):
                config_path = Path(sys.argv[index])
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
        diagnostic = {"timestamp_utc": stamp, "arguments": sys.argv[1:],
            "error_type": type(error).__name__, "error": str(error), "traceback": traceback.format_exc()}
        if config_path.exists():
            try:
                diagnostic["config_sha256"] = json_hash(json.loads(config_path.read_text("utf-8")))
            except (ValueError, OSError):
                pass
        write_json(ROOT / "research_artifacts/failures" / (stamp + ".json"), diagnostic)
        raise
