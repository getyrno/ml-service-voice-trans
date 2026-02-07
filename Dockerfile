# syntax=docker/dockerfile:1.7

############################
# Builder
############################
FROM nvidia/cuda:12.3.2-cudnn9-devel-ubuntu22.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120

# APT: кэш + ретраи + НЕ проглатываем ошибку
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    set -eux; \
    ok=0; \
    for i in 1 2 3 4 5 6 7 8; do \
      if apt-get -o Acquire::Retries=5 update && \
         apt-get -o Acquire::Retries=5 install -y --no-install-recommends --fix-missing \
           python3 python3-pip python3-venv python3-dev python-is-python3 \
           build-essential pkg-config \
           ffmpeg \
           libavformat-dev libavcodec-dev libavdevice-dev libavutil-dev libswscale-dev \
           curl ca-certificates; \
      then ok=1; break; fi; \
      echo "APT failed, retry $i" >&2; sleep $((i*2)); \
    done; \
    test "$ok" -eq 1

WORKDIR /app
COPY requirements.txt .

# venv
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# -------------------------
# PYTORCH (СТАБИЛЬНАЯ СВЯЗКА)
# -------------------------
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    set -eux; \
    pip install -U pip setuptools wheel; \
    pip uninstall -y torch torchvision torchaudio || true; \
    pip install --no-cache-dir --force-reinstall \
      torch==2.4.1+cu124 \
      torchvision==0.19.1+cu124 \
      torchaudio==2.4.1+cu124 \
      --index-url https://download.pytorch.org/whl/cu124

# Остальные зависимости
RUN --mount=type=cache,target=/root/.cache/pip,sharing=locked \
    set -eux; \
    pip install --no-cache-dir --force-reinstall -r requirements.txt

############################
# Runtime (быстрее деплой)
############################
FROM nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1

# Минимум пакетов в рантайме
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    set -eux; \
    ok=0; \
    for i in 1 2 3 4 5 6 7 8; do \
      if apt-get -o Acquire::Retries=5 update && \
         apt-get -o Acquire::Retries=5 install -y --no-install-recommends --fix-missing \
           python3 python-is-python3 \
           ffmpeg \
           ca-certificates \
           curl; \
      then ok=1; break; fi; \
      echo "APT failed, retry $i" >&2; sleep $((i*2)); \
    done; \
    test "$ok" -eq 1

# переносим готовую виртуалку
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app
COPY ./app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
