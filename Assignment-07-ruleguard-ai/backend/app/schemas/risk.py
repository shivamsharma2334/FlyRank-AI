from enum import Enum
from pydantic import BaseModel, ConfigDict, Field


class RiskRequest(BaseModel):
    request: str = Field(min_length=1, max_length=2000)


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class RiskCategory(str, Enum):
    authentication = "authentication"
    authorization = "authorization"
    input_validation = "input_validation"
    data_security = "data_security"
    rate_limiting = "rate_limiting"
    api_design = "api_design"
    other = "other"


class RiskJudgement(BaseModel):
    model_config = ConfigDict(extra="forbid")  # extra fields from the model = schema failure

    risk_level: RiskLevel
    category: RiskCategory
    requires_review: bool
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(min_length=1, max_length=500)
