# 1. Используем официальный образ Python
FROM python:3.12-slim

# 2. Устанавливаем рабочую директорию
WORKDIR /app

# 3. Устанавливаем ffmpeg, системную зависимость для обработки аудио/видео
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# 4. Копируем файл зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 5. Копируем код приложения в рабочую директорию
COPY ./app /app/app
COPY ./app/static /app/app/static

# 6. Открываем порт 8000 для доступа к API
EXPOSE 8000

# 7. Указываем команду для запуска приложения
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
