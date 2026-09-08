"""Minimal HTTP inference service for the controlled Docker benchmark.

The service loads one locally frozen and hashed model. It intentionally exposes
only health, metadata and prediction endpoints so the systems experiment does
not depend on the project's former API implementation.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import pickle
import socket
import threading
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import numpy as np


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class InferenceState:
    """Load and validate one frozen model before accepting requests."""

    def __init__(self, model_dir: Path, model_name: str) -> None:
        self.model_dir = model_dir
        self.model_name = model_name
        self.predict_lock = threading.Lock()

        manifest_path = model_dir / "manifest.json"
        schema_path = model_dir / "schema.json"
        self.manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        records = {
            item["model"]: item for item in self.manifest.get("models", [])
        }
        if model_name not in records:
            raise ValueError(f"Unknown model in frozen manifest: {model_name}")
        self.model_record = records[model_name]
        self.model_path = model_dir / self.model_record["file"]
        actual_hash = file_hash(self.model_path)
        if actual_hash != self.model_record["sha256"]:
            raise RuntimeError(
                f"Model hash mismatch: expected {self.model_record['sha256']}, "
                f"found {actual_hash}"
            )
        if file_hash(schema_path) != self.manifest["schema_sha256"]:
            raise RuntimeError("Schema hash differs from the frozen manifest")

        load_start_ns = time.perf_counter_ns()
        # The pickle is trusted because it was generated locally and hash-checked.
        self.model = pickle.loads(self.model_path.read_bytes())
        self.load_ns = time.perf_counter_ns() - load_start_ns
        self.feature_count = len(self.schema["features"])
        self.class_count = len(self.schema["class_order"])

        smoke = self.model.predict_proba(
            np.zeros((1, self.feature_count), dtype=np.float64)
        )
        if smoke.shape != (1, self.class_count):
            raise RuntimeError(f"Unexpected smoke-test shape: {smoke.shape}")

    def metadata(self) -> dict[str, Any]:
        return {
            "status": "ready",
            "model": self.model_name,
            "model_sha256": self.model_record["sha256"],
            "model_bytes": self.model_record["bytes"],
            "schema_sha256": self.manifest["schema_sha256"],
            "feature_count": self.feature_count,
            "class_count": self.class_count,
            "class_order": self.schema["class_order"],
            "load_ns": self.load_ns,
            "pid": os.getpid(),
        }

    def validate_instances(self, payload: Any) -> np.ndarray:
        if not isinstance(payload, dict) or "instances" not in payload:
            raise ValueError("Request must be an object containing 'instances'")
        instances = payload["instances"]
        if not isinstance(instances, list) or not instances:
            raise ValueError("'instances' must be a non-empty list")
        if len(instances) > 1024:
            raise ValueError("At most 1024 instances are accepted per request")
        matrix = np.asarray(instances, dtype=np.float64)
        if matrix.ndim != 2 or matrix.shape[1] != self.feature_count:
            raise ValueError(
                f"Expected shape (n, {self.feature_count}), found {matrix.shape}"
            )
        if not np.isfinite(matrix).all():
            raise ValueError("All input values must be finite numbers")
        return matrix

    def predict(self, matrix: np.ndarray) -> dict[str, Any]:
        queued_at_ns = time.perf_counter_ns()
        with self.predict_lock:
            predict_start_ns = time.perf_counter_ns()
            probabilities = self.model.predict_proba(matrix)
            predict_ns = time.perf_counter_ns() - predict_start_ns
        queue_wait_ns = predict_start_ns - queued_at_ns
        if probabilities.shape != (len(matrix), self.class_count):
            raise RuntimeError(f"Unexpected prediction shape: {probabilities.shape}")
        if not np.allclose(probabilities.sum(axis=1), 1.0, atol=1e-6):
            raise RuntimeError("Returned probabilities do not sum to one")
        return {
            "probabilities": probabilities.tolist(),
            "class_ids": np.argmax(probabilities, axis=1).astype(int).tolist(),
            "model_predict_ns": predict_ns,
            "queue_wait_ns": queue_wait_ns,
            "batch_size": len(matrix),
        }


class InferenceHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    state: InferenceState

    def log_message(self, format: str, *args: Any) -> None:
        return

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":"), allow_nan=False).encode(
            "utf-8"
        )
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in {"/health", "/metadata"}:
            self.send_json(HTTPStatus.OK, self.state.metadata())
            return
        self.send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/predict":
            self.send_json(HTTPStatus.NOT_FOUND, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if length <= 0 or length > 2_000_000:
                raise ValueError("Invalid request body size")
            payload = json.loads(self.rfile.read(length))
            matrix = self.state.validate_instances(payload)
            result = self.state.predict(matrix)
            self.send_json(HTTPStatus.OK, result)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": str(exc)})
        except Exception as exc:
            self.send_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                {"error": type(exc).__name__},
            )


class LowLatencyThreadingHTTPServer(ThreadingHTTPServer):
    """Disable Nagle on accepted sockets to avoid delayed-ACK artifacts.

    The benchmark sends small request/response bodies over persistent loopback
    connections. Without TCP_NODELAY, the standard-library server can add an
    approximately 40 ms transport delay unrelated to model inference.
    """

    def get_request(self) -> tuple[socket.socket, Any]:
        request, client_address = super().get_request()
        request.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        return request, client_address


def main() -> None:
    model_dir = Path(os.environ.get("MODEL_DIR", "/models"))
    model_name = os.environ.get("MODEL_NAME", "xgboost")
    port = int(os.environ.get("SERVICE_PORT", "8000"))
    state = InferenceState(model_dir=model_dir, model_name=model_name)
    InferenceHandler.state = state
    server = LowLatencyThreadingHTTPServer(("0.0.0.0", port), InferenceHandler)
    server.daemon_threads = True
    print(
        json.dumps(
            {
                "event": "ready",
                "model": model_name,
                "model_sha256": state.model_record["sha256"],
                "port": port,
            }
        ),
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
