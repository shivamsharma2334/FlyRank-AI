"""FastAPI app: CORS, flat error responses (400/422/500/502/503/504), the judge router.
Run (from backend/): uvicorn app.main:app --reload --port 8000
"""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.routes import router
from app.core.config import settings

app = FastAPI(title="RuleGuard AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        field = ".".join(str(p) for p in errors[0]["loc"][1:]) or "request"
        message = errors[0]["msg"]
    else:
        field, message = "request", "Invalid request body"
    return JSONResponse(status_code=400, content={"error": "validation_error", "message": f"{field}: {message}"})


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict):
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"error": "http_error", "message": str(exc.detail)})


@app.get("/health")
async def health():
    return {"status": "ok", "llm_enabled": settings.llm_enabled, "llm_stub": settings.llm_stub}


app.include_router(router)
