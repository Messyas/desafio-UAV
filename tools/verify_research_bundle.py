"""Verify a packaged research ZIP against its external and internal SHA-256 manifest."""
from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify(path: Path) -> dict:
    sidecar = path.with_suffix(".manifest.json")
    manifest = json.loads(sidecar.read_text(encoding="utf-8"))
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1 << 20):
            digest.update(block)
    if digest.hexdigest() != manifest["zip_sha256"]:
        raise ValueError(f"ZIP checksum mismatch: {path}")
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        expected = set(manifest["files_sha256"]) | {"BUNDLE_MANIFEST.json"}
        if len(names) != len(set(names)) or set(names) != expected:
            raise ValueError("Bundle entries differ from manifest or contain duplicates")
        internal = json.loads(archive.read("BUNDLE_MANIFEST.json"))
        if internal != {key: value for key, value in manifest.items() if key != "zip_sha256"}:
            raise ValueError("Internal and external manifests differ")
        for name, recorded in manifest["files_sha256"].items():
            if name.startswith("/") or ".." in Path(name).parts or "\\" in name:
                raise ValueError(f"Unsafe bundle entry: {name}")
            if sha256(archive.read(name)) != recorded:
                raise ValueError(f"Entry checksum mismatch: {name}")
    return {"archive": str(path), "entries": len(expected), "zip_sha256": manifest["zip_sha256"]}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", nargs="+", type=Path)
    for archive_path in parser.parse_args().archives:
        print(json.dumps(verify(archive_path), ensure_ascii=False))
