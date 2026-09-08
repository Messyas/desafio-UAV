"""Run the controlled local Docker HTTP benchmark for frozen UAVIDS models."""

from __future__ import annotations

import argparse
import concurrent.futures
import http.client
import json
import platform
import subprocess
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import psutil

if __package__ in {None, ""}:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from uavids_study.predictive_experiment import (  # type: ignore
        file_hash,
        json_hash,
        write_gzip_csv,
        write_json,
    )
else:
    from .predictive_experiment import file_hash, json_hash, write_gzip_csv, write_json


def docker_command(*args: str, timeout: float | None = None) -> str:
    completed = subprocess.run(
        ["docker", *args],
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return completed.stdout.strip()


def percentile_summary_ns(values: pd.Series | np.ndarray) -> dict[str, float]:
    array = np.asarray(values, dtype=np.float64)
    values_us = array / 1_000.0
    return {
        "count": int(len(values_us)),
        "mean_us": float(values_us.mean()),
        "std_us": float(values_us.std(ddof=1)) if len(values_us) > 1 else 0.0,
        "p50_us": float(np.quantile(values_us, 0.50)),
        "p95_us": float(np.quantile(values_us, 0.95)),
        "p99_us": float(np.quantile(values_us, 0.99)),
        "max_us": float(values_us.max()),
    }


def encode_instances(instances: np.ndarray) -> bytes:
    return json.dumps(
        {"instances": instances.tolist()}, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


class PersistentClient:
    def __init__(self, host: str, port: int, timeout_seconds: float) -> None:
        self.connection = http.client.HTTPConnection(
            host, port, timeout=timeout_seconds
        )

    def close(self) -> None:
        self.connection.close()

    def predict(self, body: bytes) -> tuple[int, dict[str, Any]]:
        start_ns = time.perf_counter_ns()
        self.connection.request(
            "POST",
            "/predict",
            body=body,
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(body)),
            },
        )
        response = self.connection.getresponse()
        response_body = response.read()
        duration_ns = time.perf_counter_ns() - start_ns
        if response.status != 200:
            raise RuntimeError(
                f"Prediction failed with HTTP {response.status}: "
                f"{response_body.decode('utf-8', errors='replace')}"
            )
        return duration_ns, json.loads(response_body)


def get_json(host: str, port: int, path: str, timeout: float) -> dict[str, Any]:
    connection = http.client.HTTPConnection(host, port, timeout=timeout)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        body = response.read()
        if response.status != 200:
            raise RuntimeError(f"GET {path} returned HTTP {response.status}")
        return json.loads(body)
    finally:
        connection.close()


def wait_until_ready(
    host: str, port: int, expected_model: str, timeout_seconds: float
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            metadata = get_json(host, port, "/health", timeout=2)
            if metadata.get("status") == "ready" and metadata.get("model") == expected_model:
                return metadata
        except Exception as exc:
            last_error = exc
        time.sleep(0.5)
    raise TimeoutError(f"Container did not become ready: {last_error}")


def parse_percent(value: str) -> float:
    return float(value.strip().rstrip("%"))


def parse_bytes(value: str) -> float:
    value = value.strip()
    units = {
        "B": 1.0,
        "kB": 1_000.0,
        "KB": 1_000.0,
        "KiB": 1024.0,
        "MB": 1_000_000.0,
        "MiB": 1024.0**2,
        "GB": 1_000_000_000.0,
        "GiB": 1024.0**3,
    }
    for unit in sorted(units, key=len, reverse=True):
        if value.endswith(unit):
            return float(value[: -len(unit)].strip()) * units[unit]
    raise ValueError(f"Unsupported Docker memory unit: {value}")


class DockerStatsSampler:
    def __init__(self, container_name: str, interval_seconds: float) -> None:
        self.container_name = container_name
        self.interval_seconds = interval_seconds
        self.rows: list[dict[str, Any]] = []
        self.errors: list[str] = []
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=max(10.0, self.interval_seconds * 4))

    def _run(self) -> None:
        while not self._stop.is_set():
            observed_at = datetime.now(timezone.utc).isoformat()
            try:
                raw = docker_command(
                    "stats",
                    "--no-stream",
                    "--format",
                    "{{json .}}",
                    self.container_name,
                    timeout=15,
                )
                payload = json.loads(raw.splitlines()[-1])
                memory_used = payload["MemUsage"].split("/")[0].strip()
                self.rows.append(
                    {
                        "observed_at_utc": observed_at,
                        "cpu_percent": parse_percent(payload["CPUPerc"]),
                        "memory_bytes": parse_bytes(memory_used),
                        "memory_percent": parse_percent(payload["MemPerc"]),
                        "pids": int(payload["PIDs"]),
                    }
                )
            except Exception as exc:
                self.errors.append(f"{type(exc).__name__}: {exc}")
            self._stop.wait(self.interval_seconds)


def run_individual_calls(
    inputs: np.ndarray,
    rng: np.random.Generator,
    host: str,
    port: int,
    config: dict[str, Any],
    model_name: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for repetition in range(int(config["repetitions"])):
        indices = rng.integers(
            0, len(inputs), size=int(config["individual_calls_per_repetition"])
        )
        bodies = [encode_instances(inputs[index : index + 1]) for index in indices]
        client = PersistentClient(
            host, port, float(config["request_timeout_seconds"])
        )
        try:
            for call_id, (row_id, body) in enumerate(zip(indices, bodies)):
                duration_ns, response = client.predict(body)
                if response["batch_size"] != 1 or len(response["probabilities"]) != 1:
                    raise AssertionError("Unexpected individual response shape")
                rows.append(
                    {
                        "model": model_name,
                        "repetition": repetition,
                        "call_id": call_id,
                        "row_id": int(row_id),
                        "client_duration_ns": duration_ns,
                        "server_predict_ns": int(response["model_predict_ns"]),
                        "server_queue_wait_ns": int(response["queue_wait_ns"]),
                    }
                )
        finally:
            client.close()
    return pd.DataFrame(rows)


def run_batch_calls(
    inputs: np.ndarray,
    rng: np.random.Generator,
    host: str,
    port: int,
    config: dict[str, Any],
    model_name: str,
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    client = PersistentClient(host, port, float(config["request_timeout_seconds"]))
    try:
        for repetition in range(int(config["repetitions"])):
            for batch_size in config["batch_sizes"]:
                for call_id in range(int(config["batch_calls_per_repetition"])):
                    indices = rng.integers(0, len(inputs), size=int(batch_size))
                    body = encode_instances(inputs[indices])
                    duration_ns, response = client.predict(body)
                    if response["batch_size"] != int(batch_size):
                        raise AssertionError("Unexpected batch response size")
                    rows.append(
                        {
                            "model": model_name,
                            "repetition": repetition,
                            "batch_size": int(batch_size),
                            "call_id": call_id,
                            "request_bytes": len(body),
                            "client_duration_ns": duration_ns,
                            "server_predict_ns": int(response["model_predict_ns"]),
                            "server_queue_wait_ns": int(response["queue_wait_ns"]),
                            "client_amortized_ns_per_row": duration_ns
                            / int(batch_size),
                        }
                    )
    finally:
        client.close()
    return pd.DataFrame(rows)


def throughput_worker(
    bodies: list[bytes], host: str, port: int, timeout_seconds: float, worker_id: int
) -> list[dict[str, Any]]:
    client = PersistentClient(host, port, timeout_seconds)
    rows: list[dict[str, Any]] = []
    try:
        for worker_call_id, body in enumerate(bodies):
            duration_ns, response = client.predict(body)
            rows.append(
                {
                    "worker_id": worker_id,
                    "worker_call_id": worker_call_id,
                    "client_duration_ns": duration_ns,
                    "server_predict_ns": int(response["model_predict_ns"]),
                    "server_queue_wait_ns": int(response["queue_wait_ns"]),
                }
            )
    finally:
        client.close()
    return rows


def run_throughput_calls(
    inputs: np.ndarray,
    rng: np.random.Generator,
    host: str,
    port: int,
    config: dict[str, Any],
    model_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    call_rows: list[dict[str, Any]] = []
    summary_rows: list[dict[str, Any]] = []
    total_requests = int(config["throughput_requests_per_repetition"])
    for concurrency in config["throughput_concurrency"]:
        concurrency = int(concurrency)
        for repetition in range(int(config["repetitions"])):
            indices = rng.integers(0, len(inputs), size=total_requests)
            bodies = [encode_instances(inputs[index : index + 1]) for index in indices]
            partitions = [bodies[offset::concurrency] for offset in range(concurrency)]
            wall_start_ns = time.perf_counter_ns()
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=concurrency
            ) as executor:
                futures = [
                    executor.submit(
                        throughput_worker,
                        partition,
                        host,
                        port,
                        float(config["request_timeout_seconds"]),
                        worker_id,
                    )
                    for worker_id, partition in enumerate(partitions)
                ]
                current_rows: list[dict[str, Any]] = []
                for future in futures:
                    current_rows.extend(future.result())
            wall_duration_ns = time.perf_counter_ns() - wall_start_ns
            for row in current_rows:
                row.update(
                    {
                        "model": model_name,
                        "concurrency": concurrency,
                        "repetition": repetition,
                    }
                )
            call_rows.extend(current_rows)
            summary_rows.append(
                {
                    "model": model_name,
                    "concurrency": concurrency,
                    "repetition": repetition,
                    "requests": len(current_rows),
                    "wall_duration_ns": wall_duration_ns,
                    "requests_per_second": len(current_rows)
                    / (wall_duration_ns / 1_000_000_000),
                }
            )
    return pd.DataFrame(call_rows), pd.DataFrame(summary_rows)


def warm_up(
    inputs: np.ndarray,
    rng: np.random.Generator,
    host: str,
    port: int,
    config: dict[str, Any],
) -> None:
    client = PersistentClient(host, port, float(config["request_timeout_seconds"]))
    try:
        indices = rng.integers(0, len(inputs), size=int(config["warmup_calls"]))
        for index in indices:
            _, response = client.predict(encode_instances(inputs[index : index + 1]))
            if response["batch_size"] != 1:
                raise AssertionError("Warm-up response was invalid")
    finally:
        client.close()


def inspect_container(container_name: str) -> dict[str, Any]:
    return json.loads(docker_command("inspect", container_name))[0]


def run_model(
    project_root: Path,
    config: dict[str, Any],
    inputs: np.ndarray,
    model_name: str,
) -> dict[str, Any]:
    benchmark_dir = project_root / "benchmarks" / config["benchmark_id"]
    benchmark_dir.mkdir(parents=True, exist_ok=True)
    container_name = f"uavids-{config['benchmark_id'].replace('_', '-')}-{model_name}"
    host = "127.0.0.1"
    port = int(config["host_port"])
    docker_command("rm", "-f", container_name, timeout=30) if container_exists(container_name) else None
    docker_command(
        "run",
        "--detach",
        "--name",
        container_name,
        "--cpus",
        str(config["cpu_limit"]),
        "--memory",
        str(config["memory_limit"]),
        "--pids-limit",
        "256",
        "--read-only",
        "--tmpfs",
        "/tmp:rw,noexec,nosuid,size=64m",
        "--security-opt",
        "no-new-privileges",
        "--env",
        f"MODEL_NAME={model_name}",
        "--env",
        f"OMP_NUM_THREADS={config['model_threads']}",
        "--publish",
        f"127.0.0.1:{port}:{config['container_port']}",
        config["image_tag"],
        timeout=60,
    )
    sampler: DockerStatsSampler | None = None
    try:
        metadata = wait_until_ready(
            host,
            port,
            model_name,
            float(config["startup_timeout_seconds"]),
        )
        inspect = inspect_container(container_name)
        rng = np.random.default_rng(
            int(config["random_seed"]) + config["models"].index(model_name) * 10_000
        )
        sampler = DockerStatsSampler(
            container_name, float(config["resource_sample_interval_seconds"])
        )
        sampler.start()
        warm_up(inputs, rng, host, port, config)
        individual = run_individual_calls(
            inputs, rng, host, port, config, model_name
        )
        batches = run_batch_calls(inputs, rng, host, port, config, model_name)
        throughput_calls, throughput_summary = run_throughput_calls(
            inputs, rng, host, port, config, model_name
        )
        sampler.stop()

        resources = pd.DataFrame(sampler.rows)
        if resources.empty:
            raise RuntimeError(f"No Docker resource samples: {sampler.errors}")
        individual_path = benchmark_dir / f"{model_name}__individual.csv.gz"
        batch_path = benchmark_dir / f"{model_name}__batch.csv.gz"
        throughput_calls_path = benchmark_dir / f"{model_name}__throughput_calls.csv.gz"
        throughput_summary_path = benchmark_dir / f"{model_name}__throughput_summary.csv.gz"
        resources_path = benchmark_dir / f"{model_name}__resources.csv.gz"
        write_gzip_csv(individual_path, individual)
        write_gzip_csv(batch_path, batches)
        write_gzip_csv(throughput_calls_path, throughput_calls)
        write_gzip_csv(throughput_summary_path, throughput_summary)
        write_gzip_csv(resources_path, resources)

        summary = {
            "benchmark_id": config["benchmark_id"],
            "model": model_name,
            "model_sha256": metadata["model_sha256"],
            "model_bytes": metadata["model_bytes"],
            "container_id": inspect["Id"],
            "image_id": inspect["Image"],
            "container_started_at": inspect["State"]["StartedAt"],
            "limits": {
                "nano_cpus": inspect["HostConfig"]["NanoCpus"],
                "memory_bytes": inspect["HostConfig"]["Memory"],
                "pids_limit": inspect["HostConfig"]["PidsLimit"],
            },
            "service_metadata": metadata,
            "individual_client": percentile_summary_ns(
                individual["client_duration_ns"]
            ),
            "individual_server_predict": percentile_summary_ns(
                individual["server_predict_ns"]
            ),
            "batch_client": {
                str(batch_size): percentile_summary_ns(selected["client_duration_ns"])
                for batch_size, selected in batches.groupby("batch_size")
            },
            "throughput": [
                {
                    "concurrency": int(concurrency),
                    "mean_requests_per_second": float(
                        selected["requests_per_second"].mean()
                    ),
                    "std_requests_per_second": float(
                        selected["requests_per_second"].std(ddof=1)
                    ),
                }
                for concurrency, selected in throughput_summary.groupby("concurrency")
            ],
            "resources": {
                "samples": int(len(resources)),
                "cpu_percent_p50": float(resources["cpu_percent"].quantile(0.50)),
                "cpu_percent_p95": float(resources["cpu_percent"].quantile(0.95)),
                "cpu_percent_max": float(resources["cpu_percent"].max()),
                "memory_mib_p50": float(
                    resources["memory_bytes"].quantile(0.50) / 1024**2
                ),
                "memory_mib_p95": float(
                    resources["memory_bytes"].quantile(0.95) / 1024**2
                ),
                "memory_mib_max": float(resources["memory_bytes"].max() / 1024**2),
                "sampling_errors": sampler.errors,
            },
            "files": {
                path.name: file_hash(path)
                for path in [
                    individual_path,
                    batch_path,
                    throughput_calls_path,
                    throughput_summary_path,
                    resources_path,
                ]
            },
        }
        write_json(benchmark_dir / f"{model_name}__summary.json", summary)
        print(
            f"DOCKER {model_name}: p50={summary['individual_client']['p50_us']:.2f}us "
            f"p99={summary['individual_client']['p99_us']:.2f}us "
            f"memory_max={summary['resources']['memory_mib_max']:.1f}MiB"
        )
        return summary
    except Exception:
        logs = docker_command("logs", container_name, timeout=30)
        if logs:
            print(logs)
        raise
    finally:
        if sampler is not None:
            sampler.stop()
        docker_command("rm", "-f", container_name, timeout=30)


def container_exists(container_name: str) -> bool:
    names = docker_command("ps", "-a", "--format", "{{.Names}}", timeout=30)
    return container_name in names.splitlines()


def build_report(
    project_root: Path, config: dict[str, Any], summaries: list[dict[str, Any]]
) -> None:
    report_dir = project_root / "reports" / config["benchmark_id"]
    report_dir.mkdir(parents=True, exist_ok=True)
    individual_rows = []
    batch_rows = []
    throughput_rows = []
    resource_rows = []
    for summary in summaries:
        individual_rows.append(
            {
                "model": summary["model"],
                "model_mib": summary["model_bytes"] / 1024**2,
                **summary["individual_client"],
                "server_predict_p50_us": summary["individual_server_predict"]["p50_us"],
                "server_predict_p99_us": summary["individual_server_predict"]["p99_us"],
            }
        )
        throughput_rows.extend(
            {"model": summary["model"], **row} for row in summary["throughput"]
        )
        for batch_size_text, batch_summary in summary["batch_client"].items():
            batch_size = int(batch_size_text)
            batch_rows.append(
                {
                    "model": summary["model"],
                    "batch_size": batch_size,
                    "count": batch_summary["count"],
                    "p50_ms": batch_summary["p50_us"] / 1_000,
                    "p95_ms": batch_summary["p95_us"] / 1_000,
                    "p99_ms": batch_summary["p99_us"] / 1_000,
                    "amortized_p50_us_per_row": batch_summary["p50_us"]
                    / batch_size,
                }
            )
        resource_rows.append({"model": summary["model"], **summary["resources"]})
    pd.DataFrame(individual_rows).to_csv(
        report_dir / "individual_http_latency.csv", index=False
    )
    pd.DataFrame(throughput_rows).to_csv(
        report_dir / "throughput.csv", index=False
    )
    pd.DataFrame(batch_rows).to_csv(report_dir / "batch_http_latency.csv", index=False)
    pd.DataFrame(resource_rows).to_csv(
        report_dir / "resource_usage.csv", index=False
    )

    quality_cost_rows = []
    stability_path = project_root / "results" / "stability_s2_v3" / "metrics_summary.csv"
    if stability_path.exists():
        stability = pd.read_csv(stability_path)
        for summary in summaries:
            selected = stability.loc[
                (stability["protocol"] == "S2")
                & (stability["model"] == summary["model"])
            ]
            if len(selected) != 1:
                raise AssertionError(
                    f"Expected one S2 stability row for {summary['model']}, "
                    f"found {len(selected)}"
                )
            predictive = selected.iloc[0]
            quality_cost_rows.append(
                {
                    "model": summary["model"],
                    "s2_f1_macro_mean": predictive["f1_macro__mean"],
                    "s2_f1_macro_std": predictive["f1_macro__std"],
                    "docker_http_p50_ms": summary["individual_client"]["p50_us"]
                    / 1_000,
                    "docker_http_p95_ms": summary["individual_client"]["p95_us"]
                    / 1_000,
                    "docker_http_p99_ms": summary["individual_client"]["p99_us"]
                    / 1_000,
                    "best_mean_requests_per_second": max(
                        row["mean_requests_per_second"]
                        for row in summary["throughput"]
                    ),
                    "best_throughput_concurrency": max(
                        summary["throughput"],
                        key=lambda row: row["mean_requests_per_second"],
                    )["concurrency"],
                    "model_mib": summary["model_bytes"] / 1024**2,
                    "memory_mib_max": summary["resources"]["memory_mib_max"],
                }
            )
        pd.DataFrame(quality_cost_rows).to_csv(
            report_dir / "quality_cost_tradeoff.csv", index=False
        )

    lines = [
        f"# Benchmark Docker local — {config['benchmark_id']}",
        "",
        "Ambiente: Docker Desktop com containers Linux/amd64 no host Windows. ",
        f"Limites por container: `{config['cpu_limit']} CPU` e `{config['memory_limit']}` de memória.",
        "Cada modelo foi medido em um container separado, usando o mesmo artefato congelado do benchmark local em processo.",
        "",
        "## Latência HTTP individual",
        "",
    ]
    for row in individual_rows:
        lines.append(
            f"- {row['model']}: P50 {row['p50_us'] / 1000:.3f} ms, "
            f"P95 {row['p95_us'] / 1000:.3f} ms, P99 {row['p99_us'] / 1000:.3f} ms; "
            f"P50 interno de `predict_proba` {row['server_predict_p50_us'] / 1000:.3f} ms."
        )
    lines.extend(["", "## Throughput", ""])
    for row in throughput_rows:
        lines.append(
            f"- {row['model']}, concorrência {row['concurrency']}: "
            f"{row['mean_requests_per_second']:.2f} req/s "
            f"(desvio entre repetições {row['std_requests_per_second']:.2f})."
        )
    lines.extend(["", "## Lotes", ""])
    for row in batch_rows:
        lines.append(
            f"- {row['model']}, lote {row['batch_size']}: P50 "
            f"{row['p50_ms']:.3f} ms; P99 {row['p99_ms']:.3f} ms; "
            f"P50 amortizado {row['amortized_p50_us_per_row']:.2f} µs/linha."
        )
    lines.extend(["", "## Recursos observados", ""])
    for row in resource_rows:
        lines.append(
            f"- {row['model']}: memória P50 {row['memory_mib_p50']:.1f} MiB, "
            f"P95 {row['memory_mib_p95']:.1f} MiB, máximo {row['memory_mib_max']:.1f} MiB; "
            f"CPU P95 {row['cpu_percent_p95']:.1f}%."
        )
    if quality_cost_rows:
        lines.extend(["", "## Fronteira qualidade–custo", ""])
        for row in quality_cost_rows:
            lines.append(
                f"- {row['model']}: F1-macro médio S2 "
                f"{row['s2_f1_macro_mean']:.6f} (desvio {row['s2_f1_macro_std']:.6f}); "
                f"P50 HTTP {row['docker_http_p50_ms']:.3f} ms; "
                f"artefato {row['model_mib']:.1f} MiB; "
                f"memória máxima observada {row['memory_mib_max']:.1f} MiB."
            )
        lines.append(
            "As métricas preditivas vêm da rodada de estabilidade S2 e as métricas "
            "de sistemas vêm dos artefatos reajustados em todos os dados. A tabela "
            "serve para decisão multicritério; não é uma avaliação preditiva dos "
            "artefatos de implantação nos dados usados para ajustá-los."
        )
    lines.extend(
        [
            "",
            "## Fronteiras da evidência",
            "",
            "A latência do cliente começa imediatamente antes do envio HTTP e termina após a leitura integral da resposta. "
            "A serialização do corpo no cliente ocorre antes do cronômetro; desserialização, fila, inferência, serialização da resposta e transporte local estão incluídos.",
            "",
            "O experimento mede atendimento de vetores de fluxo prontos em Docker Desktop/WSL2. "
            "Não mede extração de fluxos, rádio, mobilidade, energia, bateria, hardware ARM, tempo até detecção ou rede entre máquinas. "
            "A quota de CPU e o limite de memória são controles de recursos, não uma simulação fiel de Raspberry Pi ou Jetson.",
        ]
    )
    (report_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=project_root / "configs" / "docker_local_v2.json",
    )
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--model", choices=["xgboost", "random_forest"])
    args = parser.parse_args()
    config_path = args.config.resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    artifact_dir = (
        project_root / "artifacts" / "models" / config["artifact_set_id"]
    )
    artifact_manifest = json.loads(
        (artifact_dir / "manifest.json").read_text(encoding="utf-8")
    )
    schema = json.loads((artifact_dir / "schema.json").read_text(encoding="utf-8"))
    dataset_path = project_root / "notebooks" / "data" / "raw" / "UAVIDS-2025.csv"
    if file_hash(dataset_path) != artifact_manifest["dataset_sha256"]:
        raise RuntimeError("Dataset hash differs from the frozen model manifest")
    for record in artifact_manifest["models"]:
        if file_hash(artifact_dir / record["file"]) != record["sha256"]:
            raise RuntimeError(f"Frozen model hash mismatch: {record['model']}")

    inputs = pd.read_csv(dataset_path, usecols=schema["features"])[
        schema["features"]
    ].to_numpy(dtype=np.float64)
    if not args.skip_build:
        print(f"Building {config['image_tag']}...")
        docker_command(
            "build",
            "--tag",
            config["image_tag"],
            "--file",
            str(project_root / "Dockerfile"),
            str(project_root),
            timeout=1800,
        )
    image_inspect = json.loads(
        docker_command("image", "inspect", config["image_tag"])
    )[0]
    models = [args.model] if args.model else config["models"]
    summaries = [run_model(project_root, config, inputs, model) for model in models]
    if not args.model:
        build_report(project_root, config, summaries)
    benchmark_dir = project_root / "benchmarks" / config["benchmark_id"]
    manifest = {
        "benchmark_id": config["benchmark_id"],
        "status": "complete" if len(summaries) == len(config["models"]) else "partial",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "config_sha256": json_hash(config),
        "dataset_sha256": artifact_manifest["dataset_sha256"],
        "artifact_set_id": config["artifact_set_id"],
        "image_id": image_inspect["Id"],
        "image_repo_digests": image_inspect.get("RepoDigests", []),
        "models": [summary["model"] for summary in summaries],
        "host": {
            "platform": platform.platform(),
            "processor": platform.processor(),
            "logical_cpu_count": psutil.cpu_count(logical=True),
            "physical_cpu_count": psutil.cpu_count(logical=False),
            "memory_bytes": psutil.virtual_memory().total,
        },
        "docker_version": json.loads(
            docker_command("version", "--format", "{{json .}}")
        ),
        "docker_info": json.loads(
            docker_command("info", "--format", "{{json .}}")
        ),
    }
    write_json(benchmark_dir / "manifest.json", manifest)
    print(f"Docker benchmark models: {len(summaries)}/{len(config['models'])}")


if __name__ == "__main__":
    main()
