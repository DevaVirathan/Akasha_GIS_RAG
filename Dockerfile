# Akasha RAG — image for the API and the ingestion worker (same image, two commands).
FROM python:3.12-slim

# System deps: Tesseract for the OCR fallback on scanned PDFs.
RUN apt-get update \
 && apt-get install -y --no-install-recommends tesseract-ocr \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Python deps first for better layer caching.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# App code.
COPY src ./src
COPY scripts ./scripts
COPY migrations ./migrations
COPY alembic.ini .

ENV PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# API entrypoint: apply migrations, then serve. The worker overrides this in compose.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn akasha.api.main:app --host 0.0.0.0 --port 8000 --no-access-log"]
