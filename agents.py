from langchain.agents import AgentExecutor, create_openai_tools_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, BaseMessage, AIMessage, SystemMessage
from typing import Annotated
from langgraph.graph.message import add_messages
from typing import Sequence, TypedDict, List
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_core.output_parsers import PydanticOutputParser
from tools import KnowledgeBaseSystem
from pydantic import BaseModel, Field

class AgentState(TypedDict):
    question: str
    messages: Annotated[Sequence[BaseMessage], add_messages]
    agent1_answer: str
    agent2_answer: str
    agent3_answer: str
    critic_answer: str
    agent1_turn: bool
    agent2_turn: bool
    agent3_turn: bool

class Agent:
    """Specialized agent. Recieves Agregator message list, his previous answer and critic response. Returns his answer"""
    def __init__(self, llm: ChatOpenAI, prompt: str, agent_name: str, kb_system: KnowledgeBaseSystem):
        self.knowledge_base = kb_system
        self.agent_name = agent_name
        self.runnable = self._setUpAgent(llm, prompt)
    
    def _setUpAgent(self, llm: ChatOpenAI, prompt_text: str):
        # messages = [
        #     ("system", prompt_text),
        #     MessagesPlaceholder(variable_name="question"),
        #     MessagesPlaceholder(variable_name="messages"),
        #     MessagesPlaceholder(variable_name=f"{self.agent_name}_answer"),
        #     MessagesPlaceholder(variable_name="critic_answer")
        # ]
        messages = [
            ("system", prompt_text),
            MessagesPlaceholder(variable_name="question"),
            MessagesPlaceholder(variable_name="messages"),
            MessagesPlaceholder(variable_name=f"{self.agent_name}_answer"),
            MessagesPlaceholder(variable_name="critic_answer")
        ]       

        prompt = ChatPromptTemplate.from_messages(messages)
        return prompt | llm
    def __call__(self, state: AgentState):
        agent_input = {
            "question": [
                {"role": "user", "content": "Oryginal question: " + state["question"]}
            ],
            f"{self.agent_name}_answer": [
                {"role": "assistant", "content": "Your previous response: " + state[f"{self.agent_name}_answer"]}
            ],
            "messages": state["messages"],
            "critic_answer": [
                {"role": "assistant", "content": "Critic response: " + state["critic_answer"]}
            ]
        }
        result = self.runnable.invoke(agent_input)
        last_message = result.content
        self.knowledge_base.add_to_kb(last_message)
        return {
            f"{self.agent_name}_answer": last_message,
        }
    
class Critic:
    def __init__(self, llm: ChatOpenAI, prompt: str, kb_system: KnowledgeBaseSystem):
        self.knowledge_base = kb_system
        self.runnable = self._setUpAgent(llm, prompt)
    
    def _setUpAgent(self, llm: ChatOpenAI, prompt_text: str):
        messages = [
            ("system", prompt_text),
            MessagesPlaceholder(variable_name="question"),
            MessagesPlaceholder(variable_name="messages"),
            MessagesPlaceholder(variable_name="agent1_answer"),
            MessagesPlaceholder(variable_name="agent2_answer"),
            MessagesPlaceholder(variable_name="agent3_answer")
        ]
                
        prompt = ChatPromptTemplate.from_messages(messages)
        return prompt | llm

    def __call__(self, state: AgentState):

        agent_input = {
            "question": [
                {"role": "user", "content": "Oryginal question: " + state["question"]}
            ],
            "messages": state["messages"],
            "agent1_answer": [
                {"role": "assistant", "content": "Agent1 response: " + state["agent1_answer"]}
            ],
            "agent2_answer": [
                {"role": "assistant", "content": "Agent2 response: " + state["agent2_answer"]}
            ],
            "agent3_answer": [
                {"role": "assistant", "content": "Agent3 response: " + state["agent3_answer"]}
            ]
        }
        result = self.runnable.invoke(agent_input)
        last_message = result.content
        self.knowledge_base.add_to_kb(last_message)

        return {
            "critic_answer": last_message
        }
        # print("/033[91m" + last_message + "/033[0m")


class Aggregator:
    def __init__(self, llm: ChatOpenAI, prompt: str, tools: List[tool], kb_system: KnowledgeBaseSystem):
        self.runnable = self._setUpAgent(llm, prompt, tools)
        self.knowledge_base = kb_system
        self.first_turn = True

    def _setUpAgent(self, llm: ChatOpenAI, prompt_text: str, tools):
        messages = [
            ("system", prompt_text),
            MessagesPlaceholder(variable_name="question"),
            MessagesPlaceholder(variable_name="messages"),
            MessagesPlaceholder(variable_name="agent1_answer"),
            MessagesPlaceholder(variable_name="agent2_answer"),
            MessagesPlaceholder(variable_name="agent3_answer"),
            MessagesPlaceholder(variable_name="critic_answer")
        ]
                
        prompt = ChatPromptTemplate.from_messages(messages)
        agent = create_react_agent(llm, tools=tools)
        return prompt | agent

    def __call__(self, state: AgentState):

        agent_input = {
            "question": [
                {"role": "user", "content": "Oryginal question: " + state["question"]}
            ],
            "messages": state["messages"],
            "agent1_answer": [
                {"role": "assistant", "content": "Agent1 response: " + state["agent1_answer"]}
            ],
            "agent2_answer": [
                {"role": "assistant", "content": "Agent2 response: " + state["agent2_answer"]}
            ],
            "agent3_answer": [
                {"role": "assistant", "content": "Agent3 response: " + state["agent3_answer"]}
            ],
            "critic_answer": [
                {"role": "assistant", "content": "Critic response: " + state["critic_answer"]}
            ]
        }
        result = self.runnable.invoke(agent_input)
        last_message = result["messages"][-1].content
        self.knowledge_base.add_to_kb(last_message)

        return {
            "messages": AIMessage(last_message)
        }

class RouterResponse(BaseModel):
    message: str = Field(description="Objective for the current turn")
    agent1_turn: bool = Field(description="Should agent1 take the next turn?")
    agent2_turn: bool = Field(description="Should agent2 take the next turn?")
    agent3_turn: bool = Field(description="Should agent3 take the next turn?")

class Router:
    def __init__(self, llm: ChatOpenAI, prompt: str):
        self.runnable = self._setUpAgent(llm, prompt)

    def _setUpAgent(self, llm: ChatOpenAI, prompt_text: str):
        messages = [
            ("system", prompt_text),
            MessagesPlaceholder(variable_name="question"),
            MessagesPlaceholder(variable_name="messages"),
            MessagesPlaceholder(variable_name="agent1_answer"),
            MessagesPlaceholder(variable_name="agent2_answer"),
            MessagesPlaceholder(variable_name="agent3_answer"),
            MessagesPlaceholder(variable_name="critic_answer")
        ]
                
        prompt = ChatPromptTemplate.from_messages(messages)
        return prompt | llm.with_structured_output(RouterResponse)

    def __call__(self, state: AgentState):
        agent_input = {
            "question": [
                {"role": "user", "content": state["question"]}
            ],
            "messages": state["messages"],
            "agent1_answer": [
                {"role": "assistant", "content": state["agent1_answer"]}
            ],
            "agent2_answer": [
                {"role": "assistant", "content": state["agent2_answer"]}
            ],
            "agent3_answer": [
                {"role": "assistant", "content": state["agent3_answer"]}
            ],
            "critic_answer": [
                {"role": "assistant", "content": state["critic_answer"]}
            ]
        }
        result = self.runnable.invoke(agent_input)

        return {
            "messages": SystemMessage(result.message),
            "agent1_turn": result.agent1_turn,
            "agent2_turn": result.agent2_turn,
            "agent3_turn": result.agent3_turn
        }

