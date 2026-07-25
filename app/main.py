import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.api import router as document_router
from app.parsers import DocumentParsingError

app = FastAPI(
    title="AI Document Analysis System API",
    description="회의록, 업무보고, 공문자료 문서 파싱, AI 분석, 3단 요약, 검증 신뢰도 점수 및 대시보드 UI 연동 시스템",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Router
app.include_router(document_router)

# Custom Parsing/Validation Exception Handler
@app.exception_handler(DocumentParsingError)
async def document_parsing_error_handler(request: Request, exc: DocumentParsingError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "message": exc.message,
                "status_code": exc.status_code
            }
        }
    )

# Serve Frontend Dashboard Static Files
static_dir = "static"
os.makedirs(static_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
