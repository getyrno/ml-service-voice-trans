FROM nvidia/cuda:12.1.0-cudnn8-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    # Жёстко запрещаем onnxruntime использовать CUDA-провайдер
    ORT_DISABLE_CUSTOM_OPS=1 \
    ORT_DISABLE_MEM_PATTERN=1 \
    ORT_DISABLE_CUDA=1

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

# Сначала копируем требования
COPY requirements.txt .

# 1. Ставим GPU-версию PyTorch под CUDA 12.1
RUN python3 -m pip install --no-cache-dir \
    torch==2.5.1+cu121 \
    torchvision==0.20.1+cu121 \
    torchaudio==2.5.1 \
    --extra-index-url https://download.pytorch.org/whl/cu121

# 2. Ставим остальные зависимости
RUN python3 -m pip install --no-cache-dir -r requirements.txt

# 3. Полностью выпиливаем любые варианты onnxruntime и ставим только CPU-версию
RUN python3 -m pip uninstall -y \
        onnxruntime-gpu \
        onnxruntime-directml \
        onnxruntime-training \
        onnxruntime \
        || true && \
    python3 -m pip install --no-cache-dir "onnxruntime==1.19.2"

# Копируем исходники приложения
COPY ./app /app/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
