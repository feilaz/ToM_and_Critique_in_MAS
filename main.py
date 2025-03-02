import os
import argparse
from pathlib import Path

from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers.openai_functions import JsonOutputFunctionsParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import END, StateGraph, START

from agents import AgentState, Agent, Aggregator, Router, Critic
from config_loader import load_config, get_all_config_values
from rag import RAGSystem, create_rag_tool
from tools import KnowledgeBaseSystem, create_kb_tool
from prompts import AGGREGATOR_PROMPT, AGENT1_PROMPT, AGENT2_PROMPT, AGENT3_PROMPT , ROUTER_PROMPT, CRITIC_PROMPT, AGGREGATOR_NO_TOM, AGENT1_NO_TOM, AGENT2_NO_TOM, AGENT3_NO_TOM, ROUTER_NO_TOM, CRITIC_NO_TOM, AGENT1_NO_TOM_NO_CRITIC, AGENT2_NO_TOM_NO_CRITIC, AGENT3_NO_TOM_NO_CRITIC, AGGREGATOR_NO_TOM_NO_CRITIC, ROUTER_NO_TOM_NO_CRITIC, AGENT1_NO_CRITIC, AGENT2_NO_CRITIC, AGENT3_NO_CRITIC, AGGREGATOR_NO_CRITIC, ROUTER_NO_CRITIC

from langchain_core.tools import tool

class WorkflowManager:
    def __init__(self, config):
        self.use_ToM = True
        self.use_critic = True
        self.config = config
        self.agent_llm = self._setup_agent_llm()
        self.advanced_llm = self._setup_advanced_llm()
        self.kb_system = self._setup_kb_system()
        # self.rag_system = self._setup_rag_system()
        # self.toolbox = self._setup_toolbox()
        self.workflow = self._setup_workflow()

    def _setup_agent_llm(self):
        return ChatOpenAI(model='gpt-4o-mini')

    def _setup_advanced_llm(self):
        return ChatOpenAI(model='gpt-4o-mini')

    def _setup_kb_system(self):
        return KnowledgeBaseSystem(
            neo4j_url=self.config['NEO4J_URL'],
            neo4j_username=self.config['NEO4J_USERNAME'],
            neo4j_password=self.config['NEO4J_PASSWORD']
        )

    # def _setup_rag_system(self):
    #     return RAGSystem(
    #         chroma_db_dir=self.config['CHROMA_DB_DIR'],
    #         mra_data_path=self.config['MRA_DATA_PATH'],
    #         pd_data_path=self.config['PD_DATA_PATH'],
    #         sm_data_path=self.config['SM_DATA_PATH'],
    #         model_name=self.config['OPENAI_MODEL']
    #     )

    # def _setup_toolbox(self):
    #     return {
    #         "kb_tool": [create_kb_tool(self.kb_system)],
    #         "agent1_rag": [create_rag_tool(self.rag_system.rag_MRA)],
    #         "agent2_rag": [create_rag_tool(self.rag_system.rag_PD)],
    #         "agent3_rag": [create_rag_tool(self.rag_system.rag_SM)]
    #     }

    def _route_after_router(self, state):
        if state["agent1_turn"]:
            return "agent1"
        elif state["agent2_turn"]:
            return "agent2"
        elif state["agent3_turn"]:
            return "agent3"
        else:
            return "aggregator"

    def _route_after_agent1(self, state):
        if state["agent2_turn"]:
            return "agent2"
        elif state["agent3_turn"]:
            return "agent3"
        else:
            return "critic" if self.use_critic else "aggregator"

    def _route_after_agent2(self, state):
        if state["agent3_turn"]:
            return "agent3"
        else:
            return "critic" if self.use_critic else "aggregator"
    


    def _setup_workflow(self):

            # Decide which prompts to use
        if self.use_ToM and self.use_critic:
            agent1_prompt = AGENT1_PROMPT
            agent2_prompt = AGENT2_PROMPT
            agent3_prompt = AGENT3_PROMPT
            aggregator_prompt = AGGREGATOR_PROMPT
            critic_prompt = CRITIC_PROMPT
            router_prompt = ROUTER_PROMPT
        elif not self.use_ToM and self.use_critic:
            agent1_prompt = AGENT1_NO_TOM
            agent2_prompt = AGENT2_NO_TOM
            agent3_prompt = AGENT3_NO_TOM
            aggregator_prompt = AGGREGATOR_NO_TOM
            critic_prompt = CRITIC_NO_TOM
            router_prompt = ROUTER_NO_TOM
        elif not self.use_ToM and not self.use_critic:
            agent1_prompt = AGENT1_NO_TOM_NO_CRITIC
            agent2_prompt = AGENT2_NO_TOM_NO_CRITIC
            agent3_prompt = AGENT3_NO_TOM_NO_CRITIC
            aggregator_prompt = AGGREGATOR_NO_TOM_NO_CRITIC
            critic_prompt = None
            router_prompt = ROUTER_NO_TOM_NO_CRITIC
        else:  # self.use_ToM and not self.use_critic
            agent1_prompt = AGENT1_NO_CRITIC
            agent2_prompt = AGENT2_NO_CRITIC
            agent3_prompt = AGENT3_NO_CRITIC
            aggregator_prompt = AGGREGATOR_NO_CRITIC
            critic_prompt = None
            router_prompt = ROUTER_NO_CRITIC

        if self.use_critic:
            workflow = StateGraph(AgentState)

            workflow.add_node("agent1", Agent(self.agent_llm, agent1_prompt , "agent1", self.kb_system))
            workflow.add_node("agent2", Agent(self.agent_llm, agent2_prompt, "agent2", self.kb_system))
            workflow.add_node("agent3", Agent(self.agent_llm, agent3_prompt, "agent3", self.kb_system))
            workflow.add_node("aggregator", Aggregator(self.advanced_llm, aggregator_prompt, [create_kb_tool(self.kb_system)], self.kb_system))
            workflow.add_node("critic", Critic(self.agent_llm, critic_prompt, self.kb_system))
            workflow.add_node("router", Router(self.advanced_llm, router_prompt))

            workflow.add_edge(START, "router")
            workflow.add_conditional_edges("agent1", self._route_after_agent1)
            workflow.add_conditional_edges("agent2", self._route_after_agent2)
            workflow.add_edge("agent3", "critic")
            workflow.add_edge("critic", "aggregator")
            workflow.add_conditional_edges("aggregator", lambda state: END if not state["agent1_turn"] and not state["agent2_turn"] and not state["agent3_turn"] else "router")
            workflow.add_conditional_edges("router", self._route_after_router)

            return workflow.compile()
    
        else:

            workflow = StateGraph(AgentState)

            workflow.add_node("agent1", Agent(self.agent_llm, agent1_prompt , "agent1", self.kb_system))
            workflow.add_node("agent2", Agent(self.agent_llm, agent2_prompt, "agent2", self.kb_system))
            workflow.add_node("agent3", Agent(self.agent_llm, agent3_prompt, "agent3", self.kb_system))
            workflow.add_node("aggregator", Aggregator(self.advanced_llm, aggregator_prompt, [create_kb_tool(self.kb_system)], self.kb_system))
            workflow.add_node("router", Router(self.advanced_llm, router_prompt))

            workflow.add_edge(START, "router")
            workflow.add_conditional_edges("agent1", self._route_after_agent1)
            workflow.add_conditional_edges("agent2", self._route_after_agent2)
            workflow.add_edge("agent3", "aggregator")
            workflow.add_conditional_edges("aggregator", lambda state: END if not state["agent1_turn"] and not state["agent2_turn"] and not state["agent3_turn"] else "router")
            workflow.add_conditional_edges("router", self._route_after_router)

            return workflow.compile()


    def run_phase(self, problem: str):
        initial_state = {
            "agent1_turn": True,
            "agent2_turn": True,
            "agent3_turn": True,
            "question": problem,
            "agent1_answer": "",
            "agent2_answer": "",
            "agent3_answer": "",
            "critic_answer": "",
            "messages": []
        }
        
        for s in self.workflow.stream(initial_state, {"recursion_limit": 50}):
            if "__end__" not in s:
                print(s)
                print("----")

def main():
    # parser = argparse.ArgumentParser(description="Run multi-agent system for product development phases.")
    # parser.add_argument("problem", help="The problem statement for the phase")
    # args = parser.parse_args()

    config = load_config()
    config_values = get_all_config_values(config)

    # Set environment variables
    os.environ["OPENAI_API_KEY"] = config_values['OPENAI_API_KEY']
    if config_values['LANGCHAIN_TRACING_V2']:
        os.environ["LANGCHAIN_API_KEY"] = config_values['LANGCHAIN_API_KEY']
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_PROJECT"] = config_values['LANGCHAIN_PROJECT']
    else:
        # Remove LangChain environment variables if tracing is disabled
        for var in ["LANGCHAIN_API_KEY", "LANGCHAIN_TRACING_V2", "LANGCHAIN_PROJECT"]:
            os.environ.pop(var, None)

    # problem = "The company is considering investing in one of three emerging technologies: Edge Computing, Quantum Computing, or Blockchain. Analyze the options and recommend an investment strategy, considering technical feasibility, market potential, and financial viability. Which technology should the company invest in?"

    problem = "Our mid-sized tech firm (annual R&D budget: $12M) must choose one emerging technology to prioritize: Edge Computing, Quantum Computing, or Blockchain. Which option offers the optimal balance of technical feasibility, market potential, and financial viability over a 3-5 year horizon, considering our current capabilities in distributed systems development?"

    workflow_manager = WorkflowManager(config_values)
    workflow_manager.run_phase(problem)

if __name__ == "__main__":
    main()