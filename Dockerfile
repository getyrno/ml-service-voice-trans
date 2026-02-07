# syntax=docker/dockerfile:1.7

############################
# Builder
############################
FROM nvidia/cuda:12.3.2-cudnn9-devel-ubuntu22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120

# -------------------------
# APT deps
# -------------------------
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv python3-dev python-is-python3 \
        build-essential pkg-config \
        ffmpeg \
        libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev libswscale-dev \
        curl ca-certificates; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# -------------------------
# venv
# -------------------------
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# -------------------------
# PYTORCH (ЕДИНСТВЕННО СОВМЕСТИМЫЙ С PYANNOTE)
# -------------------------
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    set -eux; \
    pip install -U pip setuptools wheel; \
    pip uninstall -y torch torchvision torchaudio || true; \
    pip install --no-cache-dir --force-reinstall \
        torch==1.13.1+cu117 \
        torchvision==0.14.1+cu117 \
        torchaudio==0.13.1+cu117 \
        --index-url https://download.pytorch.org/whl/cu117

# -------------------------
# Python deps
# -------------------------
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    set -eux; \
    pip install --no-cache-dir --force-reinstall -r requirements.txt

############################
# Runtime
############################
FROM nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# -------------------------
# Runtime deps
# -------------------------
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        python3 python-is-python3 \
        ffmpeg \
        ca-certificates \
        curl; \
    rm -rf /var/lib/apt/lists/*

# -------------------------
# venv from builder
# -------------------------
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY ./app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
