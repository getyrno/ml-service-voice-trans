# syntax=docker/dockerfile:1.7

ARG CUDA_VER=12.3.2
ARG UBUNTU_VER=22.04
ARG PYTORCH_INDEX_URL=https://download.pytorch.org/whl/cu124
ARG APT_MIRROR=http://archive.ubuntu.com/ubuntu

############################
# 1) Builder (ставим deps)
############################
FROM nvidia/cuda:${CUDA_VER}-cudnn9-devel-ubuntu${UBUNTU_VER} AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120

# (опционально) заменить зеркало Ubuntu
RUN sed -i "s|http://archive.ubuntu.com/ubuntu|${APT_MIRROR}|g" /etc/apt/sources.list

# APT: кэш + ретраи (устойчиво к 502/timeout)
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    set -eux; \
    for i in 1 2 3 4 5; do \
      apt-get -o Acquire::Retries=5 update && \
      apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
        python3 python3-pip python3-venv python3-dev python-is-python3 \
        build-essential pkg-config \
        ffmpeg \
        libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev libswscale-dev \
        curl ca-certificates \
      && break || (echo "APT failed, retry $i" >&2; sleep $((i*3))); \
    done; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# Виртуалка (переносим в runtime как единый блок)
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# PIP: кэш + ретраи (ускоряет и делает стабильнее)
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    set -eux; \
    pip install -U pip setuptools wheel; \
    pip install --retries 10 --timeout 120 --prefer-binary \
      torch==2.5.1+cu124 torchvision==0.20.1+cu124 torchaudio==2.5.1 \
      --index-url ${PYTORCH_INDEX_URL}; \
    pip install --retries 10 --timeout 120 --prefer-binary -r requirements.txt

############################
# 2) Runtime (маленький и быстрый)
############################
FROM nvidia/cuda:${CUDA_VER}-cudnn9-runtime-ubuntu${UBUNTU_VER} AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

ARG APT_MIRROR=http://archive.ubuntu.com/ubuntu
RUN sed -i "s|http://archive.ubuntu.com/ubuntu|${APT_MIRROR}|g" /etc/apt/sources.list

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    set -eux; \
    for i in 1 2 3 4 5; do \
      apt-get -o Acquire::Retries=5 update && \
      apt-get -o Acquire::Retries=5 install -y --no-install-recommends \
        python3 python-is-python3 \
        ffmpeg \
        ca-certificates \
      && break || (echo "APT failed, retry $i" >&2; sleep $((i*3))); \
    done; \
    rm -rf /var/lib/apt/lists/*

# зависимости (venv) из builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY ./app /app/app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
