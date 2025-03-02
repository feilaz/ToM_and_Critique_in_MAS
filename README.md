# Towards Cognitive Synergy in LLM-Based Multi-Agent Systems

This repository contains the code for the CogSci submission "Towards Cognitive Synergy in LLM-Based Multi-Agent Systems: Integrating Theory of Mind and Critical Evaluation."  The project enhances collaborative reasoning in LLM-based Multi-Agent Systems (MAS) using Theory of Mind (ToM), structured criticism, and a knowledge base with logical reasoning (Neo4j and Clingo).

## Overview

The system simulates a strategic decision-making process where specialized agents (Data and Logic Specialist, Visionary Strategist, Implementation Realist), a Critic Agent, an Orchestrator, and an Integrator collaborate.  Agents predict each other's responses (ToM) and a Critic Agent identifies flaws.  A Neo4j graph database and Clingo ASP solver handle structured knowledge and logical inference.

## Project Structure
agents.py # Agent classes
config.ini # Configuration (API keys, model, paths)
config_loader.py # Configuration loading
main.py # Main workflow
prompts.py # LLM prompts
rag.py # Retrieval-Augmented Generation
README.md # This file
tools.py # Knowledge base and Clingo integration


## Installation and Setup

1.  **Clone:** `git clone <your_repository_url>`
2.  **Install:** `cd <your_repository_directory>` and `pip install langchain langchain-openai langchain-community neo4j clingo pydantic`
3.  **Neo4j:** Set up a Neo4j database (local, cloud, or sandbox: [https://sandbox.neo4j.com/](https://sandbox.neo4j.com/)). Note the Bolt URL, username, and password.
4.  **Configure:** Edit `config.ini` with your OpenAI API key, Neo4j credentials, and desired model (e.g., `gpt-4o-mini`). Optionally, set API keys as environment variables (`OPENAI_API_KEY`, `LANGCHAIN_API_KEY`).

## Running the System
1.  **Navigate:** `cd code`
2.  **Run:** `python main.py "Your problem statement here"` (replace with your desired decision-making scenario).
3. **Observe the output**: The system will print the conversation between the agents and store Knowledge Base queries in `knowledge_base_queries.json`

## Ablation Studies
*   **Disable Critic:** In `main.py`, set `self.use_critic = False` within the `WorkflowManager` class.
*   **Disable ToM:** In `main.py`, set `self.use_ToM = False` within the `WorkflowManager` class.
