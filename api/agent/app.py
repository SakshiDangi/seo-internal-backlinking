import json
from typing import Any, Dict, Optional, List
from rag_agent.src.agent import FeedbackWorkflow
from common.llms import get_llm
from common.utils import get_weaviate_client
from common.schemas import LambdaResponse, LLMConfig, FeedbackBaseRequestConfig, RequestTool, RequestHistory, \
    RagRequestConfig


def lambda_handler(event: Optional[Any], context: Optional[Any]) -> LambdaResponse:
    try:
        body: Dict[str, Any] = json.loads(event['body'])
    except TypeError:
        body: Dict[str, Any] = event['body']

    # get message and history
    history: RequestHistory = RequestHistory(messages=body['history'])
    state: int = body.get('state', 0)

    # get inputs, inputs are dict with keys as the name of the input and values as the input
    inputs: Dict[str, Any] = body['inputs']
    config: RagRequestConfig = RagRequestConfig(**body['config'])
    llm_config: LLMConfig = LLMConfig(**body['llm_config'])

    system_prompt: str = body['system_prompt']
    user_prompt: str = body['user_prompt']
    tools_list: List[str] =  body['input_tools']
    #tools = get_tools(input_tools=input_tools)
    # initialize model
    llm = get_llm(llm_config,config)
    client = get_weaviate_client(llm_config)

    seo_workflow = FeedbackWorkflow(
        inputs, system_prompt, user_prompt, llm, 150, config, history, client
    )
    seo_workflow.run()
    print(seo_workflow.final_response)
    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": seo_workflow.final_response,
                # 'intermediate_steps': steps,
            }
        ),
    }
