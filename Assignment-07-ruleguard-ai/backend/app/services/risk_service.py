"""Orchestration: kill switch -> stub mode -> RAG -> Gemini -> review threshold.
Never returns arbitrary model text; always a validated RiskJudgement or a raised exception.
"""
from app.core.config import settings
from app.core.exceptions import LLMDisabledError
from app.core.logging_utils import log_event
from app.schemas.risk import RiskCategory, RiskJudgement, RiskLevel
from app.services import gemini_service, rag_service


def _stub_result() -> RiskJudgement:
    return RiskJudgement(
        risk_level=RiskLevel.low,
        category=RiskCategory.api_design,
        requires_review=False,
        confidence=0.8,
        reason="Stub response used for local development.",
    )


async def judge(request_text: str) -> RiskJudgement:
    if not settings.llm_enabled:
        log_event("llm_disabled", request_length=len(request_text))
        raise LLMDisabledError("AI judgement is temporarily disabled.")

    if settings.llm_stub:
        log_event("assessment_success", mode="stub")
        return _stub_result()

    log_event("request_received", request_length=len(request_text))

    chunks = await rag_service.retrieve(request_text)
    context_text = rag_service.build_context(chunks)
    log_event("rag_retrieval", chunks_returned=len(chunks))

    judgement = await gemini_service.judge(request_text, context_text)

    # Safety net independent of model compliance: force human review when confidence
    # is below threshold, OR when the model itself couldn't confidently categorize
    # the request (category == "other"). See system design section 38.
    if judgement.category == RiskCategory.other or judgement.confidence < settings.review_threshold:
        judgement = judgement.model_copy(update={"requires_review": True})

    log_event("assessment_success", prompt_version=settings.prompt_version, mode="live")
    return judgement
