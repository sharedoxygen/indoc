# Tooling image for the inDoc ADK agent (local runs, demo, deploy).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HOME=/tmp

WORKDIR /workspace

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY indoc_agent ./indoc_agent
COPY scripts ./scripts
COPY tests ./tests
