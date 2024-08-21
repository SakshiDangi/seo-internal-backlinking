import re
from enum import Enum
from typing import TypedDict, Dict, Any, List

from pydantic import BaseModel, validator
from pydantic.v1 import Field


# DB schemas
class User(BaseModel):
    id: int
    email: str
    first_name: str = None
    last_name: str = None
    active: bool = None


class Website(BaseModel):
    id: int
    name: str
    description: str
    domain: str
    created_at: str
    updated_at: str


class WebsitePages(BaseModel):
    id: int
    website_id: int
    url: str
    canonical_url: str
    title: str
    description: str
    author: str
    keywords: str
    language_code: str
    text: str
    markdown: str


class UserWebsite(BaseModel):
    id: int
    user_id: int
    website_id: int


class LLMConnection(str, Enum):
    nvidia = "NVIDIA"
    aws = "BEDROCK"
    openai = "OPENAI"


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
    body: str


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
