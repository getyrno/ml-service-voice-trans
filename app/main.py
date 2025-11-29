from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.api.v1.endpoints import transcription
import os

app = FastAPI(
    title="API Распознавания Речи Sparq", 
    version="1.0",
    description="API для транскрибации (расшифровки) речи из видеофайлов."
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

app.include_router(transcription.router, prefix="/api/v1", tags=["Транскрибация"])

@app.get("/", tags=["Web UI"])
def read_root_ui():
    """
    Отдает главную страницу веб-интерфейса для загрузки видео.
    """
    return FileResponse(os.path.join("app", "static", "index.html"))
