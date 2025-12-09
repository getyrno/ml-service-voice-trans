from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.v1.endpoints import transcription, jobs
from app.services.job_worker import worker_loop
import os

app = FastAPI(
    title="API Распознавания Речи Sparq", 
    version="1.0",
    description="API для транскрибации речи из видеофайлов."
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(transcription.router, prefix="/api/v1", tags=["Транскрибация"])
app.include_router(jobs.router, prefix="/api/v1", tags=["Jobs"])

@app.on_event("startup")
async def startup_event():
    import asyncio
    asyncio.create_task(worker_loop())


@app.get("/healthz", tags=["Служебное"])
async def healthcheck():
    """Эндпоинт для проверки состояния сервиса, пока для докера, в целом можно и в оркестратор влить проверку."""
    return {"status": "ok"}

@app.get("/", tags=["Web UI"])
def read_root_ui():
    """
    Отдает главную страницу веб-интерфейса для загрузки видео.
    """
    return FileResponse(os.path.join("app", "static", "index.html"))
