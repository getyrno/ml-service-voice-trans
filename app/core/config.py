import os


WHISPER_MODEL = os.getenv("WHISPER_MODEL", "small")

# ===== STT Провайдер =====
# Выбор провайдера: "whisper" или "gigaam"
STT_PROVIDER = os.getenv("STT_PROVIDER", "whisper")

# ===== GigaAM настройки =====
# Вариант модели GigaAM-v3: e2e_rnnt, e2e_ctc, rnnt, ctc
# e2e_rnnt - рекомендуется (текст с пунктуацией и нормализацией)
GIGAAM_MODEL_VARIANT = os.getenv("GIGAAM_MODEL_VARIANT", "e2e_rnnt")

# ===== A/B тестирование =====
# Процент запросов на GigaAM (0-100)
# 0 = только Whisper, 100 = только GigaAM
STT_AB_GIGAAM_PERCENT = int(os.getenv("STT_AB_GIGAAM_PERCENT", "0"))

# ===== Async Jobs Config =====
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ORCHESTRATOR_JOB_URL = os.getenv("ORCHESTRATOR_JOB_URL", "")
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/tmp/uploads")
