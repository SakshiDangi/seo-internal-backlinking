from typing import Any
from langchain_aws import ChatBedrock
from langchain_openai import ChatOpenAI
from .schemas import LLMConfig, LLMConnection
from .utils import get_tokens

def get_llm(config: LLMConfig,extra_config) -> Any:
    if config.connection == LLMConnection.nvidia:
        return ChatOpenAI(
            openai_api_base=config.api_base,
            openai_api_key=config.api_key,
            model=config.model,
            temperature=config.temperature,
        )
    elif config.connection == LLMConnection.openai:
        return ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            openai_api_key=config.api_key,
        )
    elif config.connection == LLMConnection.aws:
        return ChatBedrock(
            model_id=config.model,
            model_kwargs=dict(temperature=config.temperature,max_tokens=get_tokens(extra_config)),
            beta_use_converse_api=False,
            credentials_profile_name="bedrock"
        )


