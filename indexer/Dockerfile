FROM python:3.12.16-slim-trixie
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
      poppler-utils tesseract-ocr libgomp1 \
    && apt-get upgrade -y --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt \
    && groupadd --system --gid 10001 rahbar \
    && useradd --system --uid 10001 --gid rahbar --no-create-home rahbar
COPY pipeline ./pipeline
USER 10001:10001
ENTRYPOINT ["python", "-m", "pipeline.run"]
