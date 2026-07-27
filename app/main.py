from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

load_dotenv()

from app.api.routes import documents, health

app = FastAPI(title="문서 분석 MVP", version="1.0.0")
app.include_router(health.router)
app.include_router(documents.router)


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def home() -> str:
    return (Path(__file__).with_name("web") / "index.html").read_text(encoding="utf-8")
