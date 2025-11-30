FROM nvidia/cuda:12.1.0-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# 1 RUN вместо трёх, + build-essential, pkg-config, ffmpeg, av-* dev
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    build-essential \
    pkg-config \
    ffmpeg \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    && rm -rf /var/lib/apt/lists/*

# ОБЯЗАТЕЛЬНО: обновляем pip, setuptools, wheel, чтобы не ловить баги старого pip
RUN python3 -m pip install --upgrade pip setuptools wheel

WORKDIR /app

COPY requirements.txt .

# ставим зависимости уже новым pip
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
