"""Pure schema/contract tests — no API, no mocked LLM. Validates the closed-output
contract itself: enums, bounds, and the strict extra='forbid' rule on RiskJudgement.
"""
import pytest
from pydantic import ValidationError

from app.schemas.risk import RiskCategory, RiskJudgement, RiskLevel, RiskRequest


def test_risk_request_accepts_valid_text():
    req = RiskRequest(request="Allow users to reset their password.")
    assert req.request == "Allow users to reset their password."


def test_risk_request_rejects_empty_string():
    with pytest.raises(ValidationError):
        RiskRequest(request="")


def test_risk_request_rejects_too_long_string():
    with pytest.raises(ValidationError):
        RiskRequest(request="x" * 2001)


def test_risk_request_accepts_max_length_boundary():
    req = RiskRequest(request="x" * 2000)
    assert len(req.request) == 2000


VALID_JUDGEMENT = dict(
    risk_level=RiskLevel.low,
    category=RiskCategory.other,
    requires_review=False,
    confidence=0.5,
    reason="ok",
)


def test_risk_judgement_accepts_valid_payload():
    judgement = RiskJudgement(**VALID_JUDGEMENT)
    assert judgement.risk_level == RiskLevel.low
    assert judgement.category == RiskCategory.other


def test_risk_judgement_rejects_unknown_risk_level():
    with pytest.raises(ValidationError):
        RiskJudgement(**{**VALID_JUDGEMENT, "risk_level": "critical"})


def test_risk_judgement_rejects_unknown_category():
    with pytest.raises(ValidationError):
        RiskJudgement(**{**VALID_JUDGEMENT, "category": "password_security"})


@pytest.mark.parametrize("confidence", [-0.01, 1.01])
def test_risk_judgement_rejects_out_of_range_confidence(confidence):
    with pytest.raises(ValidationError):
        RiskJudgement(**{**VALID_JUDGEMENT, "confidence": confidence})


@pytest.mark.parametrize("confidence", [0.0, 1.0])
def test_risk_judgement_accepts_confidence_boundaries(confidence):
    judgement = RiskJudgement(**{**VALID_JUDGEMENT, "confidence": confidence})
    assert judgement.confidence == confidence


def test_risk_judgement_rejects_empty_reason():
    with pytest.raises(ValidationError):
        RiskJudgement(**{**VALID_JUDGEMENT, "reason": ""})


def test_risk_judgement_rejects_reason_over_500_chars():
    with pytest.raises(ValidationError):
        RiskJudgement(**{**VALID_JUDGEMENT, "reason": "x" * 501})


def test_risk_judgement_rejects_extra_fields():
    with pytest.raises(ValidationError):
        RiskJudgement(**{**VALID_JUDGEMENT, "extra_field": "not allowed"})


def test_risk_judgement_rejects_missing_field():
    incomplete = {k: v for k, v in VALID_JUDGEMENT.items() if k != "reason"}
    with pytest.raises(ValidationError):
        RiskJudgement(**incomplete)


def test_risk_category_is_closed_list():
    assert {c.value for c in RiskCategory} == {
        "authentication", "authorization", "input_validation",
        "data_security", "rate_limiting", "api_design", "other",
    }


def test_risk_level_is_closed_list():
    assert {l.value for l in RiskLevel} == {"low", "medium", "high"}
