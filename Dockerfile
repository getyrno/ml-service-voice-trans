FROM nvidia/cuda:12.3.2-cudnn9-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Базовые пакеты + ffmpeg и dev-библиотеки
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    python-is-python3 \
    build-essential \
    pkg-config \
    ffmpeg \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Обновляем pip / setuptools / wheel
RUN python3 -m pip install --upgrade pip setuptools wheel

WORKDIR /app

# Копируем requirements заранее, чтобы кэш слоёв нормально работал
COPY requirements.txt .

# 1. Ставим PyTorch под CUDA 12.x (cu124) — это как раз рекомендованная связка
# для ctranslate2 >= 4.5.0 и CUDA 12.3+ 
RUN python3 -m pip install --no-cache-dir \
    torch==2.5.1+cu124 \
    torchvision==0.20.1+cu124 \
    torchaudio==2.5.1 \
    --index-url https://download.pytorch.org/whl/cu124

# 2. Ставим все остальные зависимости (faster-whisper, ctranslate2, transformers и т.д.)
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# Копируем код приложения
COPY ./app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
