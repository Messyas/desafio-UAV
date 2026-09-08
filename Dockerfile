FROM python:3.12.10-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    OMP_NUM_THREADS=4 \
    OPENBLAS_NUM_THREADS=4 \
    MKL_NUM_THREADS=4 \
    NUMEXPR_NUM_THREADS=4 \
    MODEL_DIR=/models \
    SERVICE_PORT=8000

WORKDIR /app

RUN apt-get update \
    && apt-get install --no-install-recommends -y libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt /app/requirements-docker.txt
RUN python -m pip install --no-cache-dir -r /app/requirements-docker.txt

COPY src/uavids_study/docker_inference_service.py /app/docker_inference_service.py
COPY artifacts/models/deployment_candidates_v1 /models

RUN useradd --create-home --uid 10001 benchmark \
    && chown -R benchmark:benchmark /app /models

USER benchmark

EXPOSE 8000

HEALTHCHECK --interval=5s --timeout=3s --start-period=30s --retries=12 \
    CMD python -c "import json,urllib.request; assert json.load(urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2))['status'] == 'ready'"

CMD ["python", "/app/docker_inference_service.py"]
