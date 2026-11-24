FROM python:3.11-slim-trixie
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PYTHONHASHSEED=0
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
      poppler-utils tesseract-ocr libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY api/requirements.txt /tmp/api-requirements.txt
COPY indexer/requirements.txt /tmp/indexer-requirements.txt
RUN pip install --no-cache-dir -r /tmp/api-requirements.txt -r /tmp/indexer-requirements.txt \
    && groupadd --system --gid 10001 ragops \
    && useradd --system --uid 10001 --gid 10001 --no-create-home ragops
COPY api/app ./api/app
COPY indexer/pipeline ./indexer/pipeline
COPY ragops ./ragops
COPY config ./config
COPY eval ./eval
COPY data ./data
COPY scripts/stage_ragops_batch_a.py ./scripts/stage_ragops_batch_a.py
ARG GIT_COMMIT
ENV GIT_COMMIT=${GIT_COMMIT}
USER 10001:10001
CMD ["python", "-m", "uvicorn", "ragops.api:app", "--host", "0.0.0.0", "--port", "8000"]
