import json
import os
import requests
import sys
sys.path.append('D:\\NeolenSearchtool\\Tools\\ai-agents-tools')
import gradio as gr
from agent.app import lambda_handler as simple_handler
from tool_agent.app import lambda_handler as tool_handler
from feedback_agent.app import lambda_handler as feedback_handler
from rag_agent.app import lambda_handler as rag_handler
from research.app import lambda_handler as research_handler
from custom_tool.app import lambda_handler as custom_handler
from router_agent.app import lambda_handler as router_handler
import re
def is_html(text):
    """Check if the text looks like HTML."""
    return bool(re.search(r'<html|<body|<head|<!DOCTYPE html', text, re.IGNORECASE))



def get_api_response(url_endpoint, method, headers, parameters,api_response_var):
    # Convert headers and parameters from string to dictionary
    try:
        headers = headers.replace("'", '"')
        headers = json.loads(headers) if headers else {}
    except json.JSONDecodeError:
        print("Error: Invalid JSON in headers")
        return None

    try:
        parameters = parameters.replace("'", '"')
        parameters = json.loads(parameters) if parameters else {}
    except json.JSONDecodeError:
        print("Error: Invalid JSON in parameters")
        return None

    # Make the request
    print(url_endpoint,headers,parameters,method)
    try:
        if method.upper() == 'GET':
            response = requests.get(url_endpoint, headers=headers, params=parameters)
        elif method.upper() == 'POST':
            response = requests.post(url_endpoint, headers=headers, json=parameters)
        else:
            print(f"Unsupported HTTP method: {method}")
            return None

        # Check if the request was successful
        response.raise_for_status()
        
        # Return the JSON response if possible, otherwise return text
        
        try:
            api_response_var=response.json()
            return api_response_var
        except json.JSONDecodeError:
            if is_html(response.text):
                return "Response appears to be HTML. Unable to display raw HTML content."
            else:
                return response.text

    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"



def chat_to_oai_message(chat_history):
    """
   Convert chat history to OpenAI message format.

   Args:
       chat_history (list): A list of lists, where each inner list contains the user's message and the assistant's response.

   Returns:
       list: A list of dictionaries in the OpenAI message format.
   """
    messages = []
    for msg in chat_history:
        messages.append(
            {
                "content": msg[0].split()[0] if msg[0].startswith("exitcode") else msg[0],
                "role": "user",
            }
        )
        messages.append({"content": msg[1], "role": "assistant"})
    return messages


def get_response(
        agent, tools, inputs, system_prompt, user_prompt, history,
        connection, api_base, api_key, model, temperature,
        split_type, min_length_output, max_length_output,recursion_limit, intermediate_steps, feedback_limit, collections
):
    
    print(tools)

    body = {
        "inputs": {item[0]: item[1] for item in inputs.values},
        "history": chat_to_oai_message(history),
        "system_prompt": system_prompt,
        "input_tools": tools,
        "user_prompt": user_prompt,
        "llm_config": {
            "connection": connection,
            "api_base": api_base,
            "api_key": api_key,
            "model": model,
            "temperature": temperature,
        },
        "config": {
            "split_type": split_type,
            "min_length_output": min_length_output,
            "max_length_output": max_length_output,
            "recursion_limit": recursion_limit,
            "return_intermediate_steps": intermediate_steps,
            "feedback_limit": feedback_limit,
            "collections": collections,
        },
    }

    handler = {
        "simple": simple_handler,
        "tool": tool_handler,
        "feedback": feedback_handler,
        "rag": rag_handler,
        "research": research_handler,
        "custom_tool": custom_handler,
        "Agent": router_handler
    }[agent]

    response = handler({"body": json.dumps(body)}, None)
    assistant_message = json.loads(response["body"])["message"]

    tool_message = json.loads(response.get('tool_output', '{}')).get('message', 'No tool response\n')

    parsed_message = json.loads(response.get('parsed', '{}')).get('message', {})
    url_endpoint_var = parsed_message.get('url_endpoint',None)
    method_var = parsed_message.get('method',None)
    headers_var = parsed_message.get('headers', None)
    parameters_var = parsed_message.get('parameters', None)

    return history + [(user_prompt, assistant_message)],url_endpoint_var, method_var, headers_var, parameters_var


css = """
.chatbot-area {max-width: 100vw; max-height: 100vh;}
.logo-img img {width: 50px;}
.table {overflow: auto;}
"""

with gr.Blocks(css=css, elem_classes="chatbot-area") as demo:
    with gr.Row():
        with gr.Column(scale=12):
            gr.HTML("<center>"
                    + "<h1>Neoleads AI Agents</h2></center>")
        gr.Image(value='frontend/assets/neoleads-logo.svg', elem_classes="logo-img", container=False)

    with gr.Row():
        with gr.Column(scale=8):
            chatbot = gr.Chatbot(
                avatar_images=("frontend/assets/456322.webp", "frontend/assets/neoleads-logo.svg"),
                show_copy_button=True,
                height=425,
            )

            with gr.Row():
                user_prompt = gr.Textbox(
                    label="User Prompt (use variables in {} format)",
                    lines=5,
                    max_lines=5,
                    interactive=True,
                    value="""Webinar transcript: {webinar_transcript}
                    Write a concise webinar summary focusing on the key learnings from the webinar transcript 
                    provided. Follow the webinar summary structure outlined above."""
                )

            with gr.Row():
                with gr.Column(scale=4):
                    clear = gr.Button("🗑️ Clear All Message", variant='secondary')
                with gr.Column(scale=4):
                    submitBtn = gr.Button("\n💬 Send\n", size="lg", variant="primary")

        with gr.Column(scale=4):
            with gr.Tab(label="Inputs"):
                agent = gr.Dropdown(
                    choices=[
                        ("Simple Agent", "simple"), ("Tool Agent", "tool"),
                        ("Feedback Agent", "feedback"), ("RAG Agent", "rag"),
                        ('Research', 'research'),("Custom Tool","custom_tool"),
                        ('Agent', 'Agent')
                    ],
                    label="Agent",
                    value="simple",
                    interactive=True
                )
                tools = gr.Dropdown(
                    choices=[
                        ("Google Search", "google_search_common"),
                        ("Uber Suggest", "uber_suggest"),
                        ("Suggested Keywords (DataSEO)", "data_seo_keyword_suggestion"),
                        ("Metric For Matching Keyword", "data_seo_keyword"),
                        ("Suggested Keywords","uber_suggest_suggestion"),
                        ("Website Keywords","uber_suggest_url_common"),
                        ("Website Scraper", "apify_website_scraper_common"),
                        ("Metric For Domain Keywords",'data_seo_domain_keyword'),
                        ("DataForSeo Search",'data_seo_search'),
                        ("DataForSeo Search Json",'data_seo_search_json'),
                        ("Brave Search",'brave_search'),
                        ("Search API Search",'search_api'),
                        ("You Search",'you_search'),
                        ("Google Trends",'google_trends_search'),
                    ],
                    label="Tools",
                    interactive=True,
                    multiselect=True
                )
                collections = gr.Dropdown(
                    choices=[
                        ("LinkedIn Posts", "LinkedinPosts"),
                        ("LinkedIn", "LinkedinCollection"),
                        ("Google Knowledge", "GoogleCollection"),
                    ],
                    label="Knowledge",
                    value=None,
                    interactive=True,
                    multiselect=True
                )
                inputs = gr.Dataframe(
                    headers=["Key", "Value"],
                    datatype=["str", "str"],
                    row_count=(1, "dynamic"),  # Start with 1 row, allow dynamic addition
                    col_count=(2, "fixed"),  # Fixed number of columns
                    interactive=True,
                    label="Variables",
                    wrap=True,
                    value=[["name", "sumit"]],
                )
                system_prompt = gr.Textbox(
                    label="Generator Prompt (use variables in {} format)",
                    lines=5,
                    max_lines=5,
                    interactive=True,
                    value="""You are an helpful assistant."""
                )

            with gr.Tab(label="API Testing"):
                with gr.Row():
                    url_endpoint = gr.Textbox(label="URL Endpoint", interactive=True)
                
                with gr.Row():
                    method = gr.Dropdown(
                        choices=["GET", "POST"],
                        label="Method",
                        interactive=True
                    )
                with gr.Row():
                    headers = gr.Textbox(label="Headers", interactive=True)
                with gr.Row():
                    parameters = gr.Textbox(label="Parameters", interactive=True)
                with gr.Row():
                    api_response_var = gr.State()
                    api_response = gr.Textbox(label="Response", interactive=True)
                with gr.Column():
                    test = gr.Button("\nTest\n", size="sm", variant="primary")

            with gr.Tab(label="LLM Configuration"):
                connection = gr.Dropdown(
                    choices=["NVIDIA", "BEDROCK", "OPENAI"],
                    label="Connection",
                    value="BEDROCK",
                    interactive=True
                )
                api_base = gr.Textbox(
                    label="API Base",
                    interactive=True
                )
                api_key = gr.Textbox(
                    label="API Key",
                    type="password",
                    interactive=True
                )
                model = gr.Dropdown(
                    choices=[
                        "meta/llama3-70b-instruct",
                        "anthropic.claude-3-sonnet-20240229-v1:0",
                        "gpt-4o",
                        "anthropic.claude-3-haiku-20240307-v1:0"
                    ],
                    label="Model",
                    value="anthropic.claude-3-haiku-20240307-v1:0",
                    interactive=True
                )
                temperature = gr.Slider(
                    minimum=0.1,
                    maximum=1.0,
                    value=0.50,
                    step=0.01,
                    interactive=True,
                    label="Temperature",
                )

            with gr.Tab(label="Extra Configuration"):
                split_type = gr.Dropdown(
                    choices=["character", "word"],
                    label="Connection",
                    value="character",
                    interactive=True
                )
                min_length_output = gr.Number(
                    label="Min Length Output",
                    value=200,
                    interactive=True
                )
                max_length_output = gr.Number(
                    label="Max Length Output",
                    value=2500,
                    interactive=True
                )
                recursion_limit = gr.Number(
                    label="Recursion Limit",
                    value=50,
                    interactive=True
                )
                gr.Markdown("""For feedback agent.""")
                intermediate_steps = gr.Dropdown(
                    choices=[True, False],
                    label="Intermediate Steps",
                    value=False,
                    interactive=True
                )
                feedback_limit = gr.Number(
                    label="Feedback Limit",
                    value=0,
                    interactive=True
                )
    
    test.click(get_api_response, [url_endpoint, method, headers, parameters,api_response_var], api_response,queue=False)

    submitBtn.click(
        get_response,
        [
            agent, tools, inputs, system_prompt, user_prompt, chatbot,
            connection, api_base, api_key, model, temperature,
            split_type, min_length_output, max_length_output,recursion_limit, intermediate_steps, feedback_limit, collections
        ], [chatbot, url_endpoint, method, headers, parameters], queue=False)

    clear.click(lambda: None, None, chatbot, queue=False)

if __name__ == "__main__":
    if os.getenv('STAGE') == "dev":
        auth = None
    else:
        auth = ("guest@neoleads.com", "Neoleads@123")
    demo.launch(auth=auth)
