"""Obtain the canonical dataset without DVC; preserve and verify existing files."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]


def verify_dataset(path: Path, source: dict) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1 << 20):
            digest.update(chunk)
    observed = digest.hexdigest()
    if path.stat().st_size != source["bytes"] or observed != source["sha256"]:
        raise ValueError(
            f"Dataset identity mismatch: {path}. Existing files are not overwritten. "
            f"Observed SHA-256: {observed}"
        )
    return observed


def fetch_dataset(destination: Path, source: dict, *, verify_only: bool = False) -> str:
    if destination.exists():
        return verify_dataset(destination, source)
    if verify_only:
        raise FileNotFoundError(f"Dataset not found: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = Request(source["download_url"], headers={"User-Agent": "UAVIDS-research/1.0"})
    with tempfile.NamedTemporaryFile(
        dir=destination.parent, suffix=".part", delete=False
    ) as stream:
        temporary_path = Path(stream.name)
    try:
        with urlopen(request, timeout=60) as response, temporary_path.open("wb") as stream:
            while chunk := response.read(1 << 20):
                stream.write(chunk)
        observed = verify_dataset(temporary_path, source)
        # rename refuses an existing destination on Windows. No replacement of raw data.
        if destination.exists():
            return verify_dataset(destination, source)
        temporary_path.rename(destination)
        return observed
    finally:
        temporary_path.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    source = json.loads((ROOT / "provenance" / "data_source.json").read_text("utf-8"))
    destination = ROOT / source["destination"]
    observed = fetch_dataset(destination, source, verify_only=args.verify_only)
    print(f"Verified {destination}\nSHA-256: {observed}")


if __name__ == "__main__":
    main()
