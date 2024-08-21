import functools
from typing import Annotated, Sequence, TypedDict, Literal
import uuid
from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage
)
from common.schemas import RequestHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langgraph.graph import END, StateGraph, START, add_messages
import xml.etree.ElementTree as ET
from common.utils import convert_message_to_dict

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    sender: str
    limit: int


class RagAgent:
    def __init__(self, client):
        self.weaviate_client = client

    def parser(self, message):
        start = message.find("<RAG>")
        end = message.find("</RAG>") + len("</RAG>")

        # Extrair a string XML
        xml_string = message[start:end]

        # Análise da string XML
        root = ET.fromstring(xml_string)
        collection_name = root.find(".//collection_name").text
        query = root.find(".//query").text
        return collection_name, query

    def rag_node(self, state):
        """Create RAG Agent."""
        messages = state["messages"]
        last_message = messages[-1]
        collection, query = self.parser(last_message.content)
        Linkedin = self.weaviate_client.collections.get(collection)
        response = Linkedin.query.near_text(
            query=query,
            limit=10
        )
        self.weaviate_client.close()
        data = []
        for res in response.objects:
            data.append(res.properties)

        result = HumanMessage(content=str(data), name=last_message.name)
        cnt = last_message.limit
        return {
            "messages": [result],
            "sender": last_message.name,
            'limit': cnt
        }


class FeedbackAgent:
    def __init__(self, llm, inputs, collection_name, history, system_message: str = None):
        self.llm = llm
        self.system_message = system_message
        self.inputs = inputs
        self.collection_name = collection_name
        self.history = history
        self.agent = self.create_reviewer_agent()
        if system_message is not None:
            self.agent = self.create_generator_agent()

    def create_reviewer_agent(self):
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a Review and critique AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards giving proper feedback."
                    " prefix your response with FINAL REVIEW or CONTINUE so the team knows to stop or continue."
                    " prefix will be FINAL REVIEW  If there's not much to review"
                    " prefix will be CONTINUE if you have a critique and give critique as well",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        return prompt | self.llm

    def create_generator_agent(self):
        """Create an agent."""
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    " You are a helpful AI assistant, collaborating with other assistants."
                    " You have access to following collection name: {collection}\n"
                    " Use the provided collection to progress towards answering the question."
                    " If you are unable to fully answer, that's OK, another assistant with different tools "
                    " will help where you left off. Execute what you can to make progress."
                    "You 2 kind of responses:\n"
                    "1. if you need data then provide output in this below format:"
                    """
                        <RAG>
                        <collection_name>$COLLECTION_NAME</collection_name>
                        <query>$QUERY</query>
                        </RAG>
                    """
                    "2. If message receive with FINAL REVIEW than only prefix your response with FINAL ANSWER"
                    " {system_message}",
                ),
                MessagesPlaceholder(variable_name="history"),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        prompt = prompt.partial(history=self.history.dict()['messages'])
        prompt = prompt.partial(system_message=self.system_message)
        prompt = prompt.partial(collection=", ".join([collection for collection in self.collection_name]))
        return prompt | self.llm

    def agent_node(self, state, name):
        result = self.agent.invoke(state)
        if isinstance(result, ToolMessage):
            pass
        else:
            cnt = state['limit']
            if name == 'reviewer':
                cnt = cnt - 1
            result = HumanMessage(**result.dict(exclude={"type", "name"}), name=name,limit=cnt)
        return {
            "messages": [result],
            "sender": name,
            'limit': cnt
        }


class FeedbackWorkflow:
    def __init__(self, inputs, generator_system_message, user_prompt, llm, limit, config, history: [RequestHistory],
                 client):
        self.inputs = inputs
        self.generator_system_message = self.convert_prompt(generator_system_message, inputs)
        self.user_prompt = self.convert_prompt(user_prompt, inputs=inputs)
        self.llm = llm
        self.feedback_limit = config.feedback_limit
        self.collection_name = config.collections
        self.intermediate_steps = []
        self.final_response = []
        self.history = history
        self.client = client
        self.recursion_limit = limit
        self.workflow = self.create_workflow()

    def convert_prompt(self, prompt, inputs):
        input_variables = [key for key, value in inputs.items()]
        template = PromptTemplate(template=prompt, input_variables=input_variables)
        return template.invoke(inputs).text

    def create_workflow(self):

        generator_agent = FeedbackAgent(self.llm, self.inputs, self.collection_name, self.history,
                                        self.generator_system_message)
        reviewer_agent = FeedbackAgent(self.llm, self.inputs, self.collection_name, self.history)
        rag_node = RagAgent(self.client)
        workflow = StateGraph(AgentState)

        workflow.add_node("generator", functools.partial(generator_agent.agent_node, name="generator"))
        workflow.add_node("reviewer", functools.partial(reviewer_agent.agent_node, name="reviewer"))
        workflow.add_node("rag", rag_node.rag_node)
        workflow.add_conditional_edges(
            "generator",
            self.router,
            {"continue": "reviewer", "rag": "rag", "__end__": END},
        )
        workflow.add_conditional_edges(
            "reviewer",
            self.router,
            {"continue": "generator", "rag": "rag", "__end__": END},
        )

        workflow.add_conditional_edges(
            "rag",
            lambda x: x["sender"],
            {
                "generator": "generator",
                "reviewer": "reviewer",
            },
        )
        workflow.add_edge(START, "generator")

        return workflow.compile()

    def router(self, state) -> Literal["rag", "__end__", "continue"]:
        messages = state["messages"]
        last_message = messages[-1]
        print(last_message)
        if '<RAG>' in last_message.content:
            return "rag"
        if "FINAL ANSWER" in last_message.content:
            return '__end__'
        if last_message.name == 'generator' and last_message.limit != 0:
            return "continue"
        elif last_message.name == "reviewer":
            return "continue"
        elif last_message.limit == 0:
            return "__end__"
        else:
            return "continue"
        
    def convert_intermediate_steps(self,messages):
        converted_messages = []
        for message in messages:
            for key, value in message.items():
                if key == 'generator':
                    converted_messages.append({
                        'generator': {
                            'messages': [convert_message_to_dict(msg) for msg in value['messages']],
                            'sender': value.get('sender'),
                            'limit': value.get('limit')
                        }
                    })
                elif key == 'rag':
                    converted_messages.append({
                        'rag': {
                            'messages': [convert_message_to_dict(msg) for msg in value['messages']]
                        }
                    })
                elif key == 'reviewer':
                     converted_messages.append({
                        'reviewer': {
                            'messages': [convert_message_to_dict(msg) for msg in value['messages']],
                            'sender': value.get('sender'),
                            'limit': value.get('limit')
                        }
                    })
                     
        return converted_messages

    def run(self):
        events = self.workflow.stream(
            {
                "messages": [
                    HumanMessage(
                        content=self.user_prompt
                    )
                ],
                "limit": self.feedback_limit
            },
            {"recursion_limit": self.recursion_limit},
        )
        self.intermediate_steps=self.convert_intermediate_steps(events)
        for output in reversed(self.intermediate_steps):
            if 'generator' not in output:
                continue
            if 'tool_calls' in output['generator']['messages']:
                continue
            self.final_response=output['generator']['messages'][-1]['content']
            break
