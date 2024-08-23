import re
from enum import Enum
from typing import TypedDict, Dict, Any, List

from pydantic import BaseModel, validator
from pydantic.v1 import Field


class LLMConnection(str, Enum):
    nvidia = "NVIDIA"
    aws = "BEDROCK"
    openai = "OPENAI"


# Request Input schemas

class EventType(str, Enum):
    scraping = "scraping"
    saving = "saving"


class RequestBody(BaseModel):
    """
    Base request input schema
    """
    website_id: str | int
    user_id: str | int
    urls: List[str]
    event: EventType


class ApifyWebhookData(BaseModel):
    eventType: str
    userId: str
    actorId: str
    actorTaskId: str
    actorRunId: str
    startedAt: str
    finishedAt: str


class MetadataFilter(BaseModel):
    key: str
    value: str
    operator: str


class SplitType(str, Enum):
    word = "work"
    char = "character"


class LLMConfig(BaseModel):
    """
    Advanced configuration for the model
    """
    connection: LLMConnection
    api_base: str
    api_key: str
    model: str
    temperature: float


class RequestHistoryMessage(BaseModel):
    role: str
    content: str


class RequestHistory(BaseModel):
    """
    Advanced configuration for the model
    """
    messages: List[RequestHistoryMessage]


class LambdaResponse(TypedDict):
    statusCode: int
    body: Dict[str, Any]


class BaseRequestConfig(BaseModel):
    """
    Advanced configuration for the model
    """
    split_type: SplitType
    min_length_output: int
    max_length_output: int
    recursion_limit: int


class FeedbackBaseRequestConfig(BaseRequestConfig):
    """
    Advanced configuration for the model
    """
    return_intermediate_steps: bool
    feedback_limit: int


class RagRequestConfig(FeedbackBaseRequestConfig):
    """
    Advanced configuration for the model
    """
    files: List[str] = Field(default=[])
    use_all_files: bool = False


class RequestConfig(RagRequestConfig):
    pass


def validate_name(value: str) -> str:
    pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
    if not pattern.match(value):
        raise ValueError('name must match the pattern ^[a-zA-Z0-9_-]+$')
    return value


class RequestTool(BaseModel):
    """
    Advanced configuration for the model
    """
    name: str = Field(validator=validate_name)
    description: str
    api_url: str
    method: str
    input_json_schema: dict
    headers: Dict[str, str]
    path: Dict[str, str]
    body: Dict[str, Any]
    params: Dict[str, str]
