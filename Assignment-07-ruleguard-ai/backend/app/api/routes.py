"""Single endpoint. Route stays thin: validation on the Pydantic model, orchestration
in risk_service, HTTP status mapping here only."""
from fastapi import APIRouter, HTTPException

from app.core.exceptions import LLMDisabledError, LLMProviderError, LLMTimeoutError, LLMValidationError
from app.core.logging_utils import log_event
from app.schemas.risk import RiskJudgement, RiskRequest
from app.services import risk_service

router = APIRouter()


@router.post("/api/v1/risk/judge", response_model=RiskJudgement)
async def judge_risk(payload: RiskRequest) -> RiskJudgement:
    try:
        return await risk_service.judge(payload.request)
    except LLMDisabledError:
        raise HTTPException(503, detail={"error": "llm_disabled", "message": "AI judgement is temporarily disabled."})
    except LLMTimeoutError:
        raise HTTPException(504, detail={"error": "llm_timeout", "message": "The AI service did not respond within the configured timeout."})
    except LLMValidationError:
        raise HTTPException(422, detail={"error": "invalid_llm_output", "message": "The model response could not be validated after one repair attempt."})
    except LLMProviderError as exc:
        raise HTTPException(exc.status_code, detail={"error": "provider_error", "message": "The AI provider returned an error."})
    except HTTPException:
        raise
    except Exception as exc:
        # Last-resort safety net: an unclassified failure (e.g. a missing FAISS index,
        # a bug) must never leak a raw traceback to the caller. Logged for triage,
        # returned as a controlled, flatly-shaped 500 like every other error path.
        log_event("unhandled_error", error=exc.__class__.__name__, message=str(exc))
        raise HTTPException(500, detail={"error": "internal_error", "message": "An unexpected error occurred while producing the judgement."})
