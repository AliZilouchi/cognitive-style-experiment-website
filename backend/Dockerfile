# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=1000 \
    PIP_RETRIES=20 \
    CORPUS_ROOT=/app/corpus \
    INDEX_DIR=/app/data/index \
    HF_HOME=/app/data/huggingface

WORKDIR /app

# Upgrade pip so interrupted downloads can resume.
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade "pip==26.2.1"

# CPU-only PyTorch. No CUDA toolkit, cuDNN, or NVIDIA packages.
# This is kept as a separate cached layer.
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install \
      --timeout 1000 \
      --retries 20 \
      --resume-retries 20 \
      "torch==2.12.1" \
      --index-url https://download.pytorch.org/whl/cpu

# Install the remaining dependencies separately.
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install \
      --timeout 1000 \
      --retries 20 \
      --resume-retries 20 \
      "setuptools>=69" \
      "fastapi>=0.115,<1" \
      "uvicorn[standard]>=0.30,<1" \
      "numpy>=1.26,<3" \
      "langchain-core>=0.3,<2" \
      "langgraph>=0.2,<2" \
      "langchain-together>=0.3,<2" \
      "langchain-groq>=0.3,<2" \
      "together>=1.3,<3" \
      "sentence-transformers>=3,<6"

# Application changes no longer invalidate the expensive dependency layers.
COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --no-build-isolation --no-deps .

COPY corpus ./corpus
COPY scripts ./scripts

RUN mkdir -p /app/data/index /app/data/huggingface && \
    useradd --create-home appuser && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["sh", "-c", "exec uvicorn sepid_rag.api:app --host 0.0.0.0 --port ${PORT:-8000}"]
