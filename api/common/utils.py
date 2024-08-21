import os
from typing import Any
import json
import xml.etree.ElementTree as ET
from typing import Union, Dict, List, Any
import weaviate
from weaviate.config import AdditionalConfig
from common.schemas import LLMConfig, LLMConnection
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    ToolMessage
)
import re
from supabase import create_client
def get_weaviate_client(config: LLMConfig, version="v4") -> Any:
    headers = {}
    if config.connection == LLMConnection.openai:
        headers = {
            "X-OpenAI-Api-Key": config.api_key  # Replace with your inference API key
        }

    elif config.connection == LLMConnection.aws:
        headers = {
            "X-AWS-Access-Key": os.getenv("AWS_ACCESS_KEY"),
            "X-AWS-Secret-Key": os.getenv("AWS_SECRET_KEY"),
        }

    if version == "local":
        return weaviate.connect_to_custom(
            http_host=os.getenv('WEAVIATE_CLUSTER_URL'),
            http_port=8080,
            http_secure=False,
            grpc_host=os.getenv('WEAVIATE_CLUSTER_URL'),
            grpc_port=50051,
            grpc_secure=False,
            headers=headers,
            additional_config=AdditionalConfig(
                timeout=weaviate.config.Timeout(init=30, query=60, insert=120)  # Values in seconds
            ),
            # auth_credentials=AuthCredentials(
            #     api_key=os.getenv("WEAVIATE_API_KEY")
            # ),
        )
    elif version == "v4":
        return weaviate.connect_to_wcs(
            cluster_url=os.getenv("WEAVIATE_CLUSTER_URL"),
            auth_credentials=weaviate.auth.AuthApiKey(os.getenv("WEAVIATE_API_KEY")),
            headers=headers,
        )
    elif version == "v3":
        return weaviate.Client(
            url=os.getenv("WEAVIATE_CLUSTER_URL"),  # Replace with your Weaviate endpoint
            auth_client_secret=weaviate.auth.AuthApiKey(api_key=os.getenv("WEAVIATE_API_KEY")),
            additional_headers=headers
        )
    
def get_supabase_client() -> Any:
    return create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_KEY")
    )

def get_tokens(config,avg_tokens_per_word=1.5)->int:
    output_length=int(config.max_length_output)
    output_tokens = int(output_length * avg_tokens_per_word)
    return int(output_tokens*1.1)


def convert_message_to_dict(message):
    if isinstance(message, AIMessage):
        return {
            'content': message.content,
            'additional_kwargs': message.additional_kwargs,
            'response_metadata': message.response_metadata,
            'id': message.id,
            'tool_calls': message.tool_calls,
            'usage_metadata': message.usage_metadata
        }
    elif isinstance(message, ToolMessage):
        return {
            'content': message.content,
            'name': message.name,
            'id': message.id,
            'tool_call_id': message.tool_call_id
        }
    elif isinstance(message, HumanMessage):
        return {
            'content': message.content,
            'additional_kwargs': message.additional_kwargs,
            'response_metadata': message.response_metadata,
            'name': message.name,
            'id': message.id,
            'invalid_tool_calls': getattr(message, 'invalid_tool_calls', None),
            'usage_metadata': getattr(message, 'usage_metadata', None),
            'limit': getattr(message, 'limit', None),
            'tool_calls': getattr(message, 'tool_calls', None)
        }
    else:
        raise TypeError("Unsupported message type")
    


def parser(message):
    start = message.find("<apis>")
    end = message.find("</apis>") + len("</apis>")
    xml_string = message[start:end]
    xml_string = xml_string.replace("&", "&amp;")
    root = ET.fromstring(xml_string)
    apis=[]
    for api in root.findall('api'):
        url_endpoint = api.find('url_endpoint').text
        method = api.find('method').text
        headers =  json.loads(api.find('headers').text.strip())
        parameters = json.loads(api.find('parameters').text.strip())
    
        apis.append({
            "url_endpoint": url_endpoint,
            "method": method,
            "headers": headers,
            "parameters": parameters,
        })

    return apis

def extract_and_replace_xml(text):
    # Regular expression to match the XML content
    xml_pattern = re.compile(r'(<apis>.*?</apis>)', re.DOTALL)
    
    # Find the XML content
    match = xml_pattern.search(text)
    
    if match:
        xml_content = match.group(1)
        
        # Replace the XML content with a placeholder in the original text
        modified_text = text.replace(xml_content, '{placeholder}')
        
        return xml_content, modified_text
    else:
        return None, text