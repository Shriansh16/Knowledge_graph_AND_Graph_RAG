# 🧠 Neo4j-LangChain RAG Pipeline with Wikipedia and OpenAI

This repositories demonstrates a hybrid Retrieval-Augmented Generation (RAG) pipeline that extracts knowledge from Wikipedia, converts it into a graph-based representation using Neo4j, stores it with semantic search capabilities, and uses OpenAI GPT models to provide enriched, context-aware responses to user queries.

## 🔍 Project Overview

The workflow follows these main steps:

### Environment and Credential Setup
- Loads environment variables using `dotenv`.
- Requires credentials for Neo4j Aura and OpenAI API.

### Knowledge Extraction from Wikipedia
- Retrieves content for a topic (e.g., The Roman Empire).
- The content is tokenized into manageable chunks for better LLM processing.

### Graph Construction from Text
- Each chunk is transformed into a structured graph format using `LLMGraphTransformer`.
- The graphs contain nodes (entities) and edges (relationships).
- These are stored in the Neo4j graph database, optionally retaining the original source text.

### Vector Index Creation in Neo4j
- Generates embeddings using OpenAI and stores them in Neo4j.
- Enables hybrid retrieval (semantic + full-text) for unstructured chunks.

### Entity Extraction from User Queries
- Uses a dedicated prompt chain to extract named entities (like people and organizations) from user questions.
- GPT is used to output structured entities that are then mapped to Neo4j nodes.

### Graph Search
- A fuzzy full-text index query is used to find relevant nodes in the graph.
- The relationships around these nodes are explored and returned in readable format.

### Hybrid Retrieval Strategy
- Structured retrieval via graph database (Neo4j).
- Unstructured retrieval via vector similarity search using embedded Wikipedia chunks.
- Both are combined to create a rich contextual answer base.

### Question Reformulation (for Conversational Context)
- Handles follow-up questions by condensing the conversation history into a standalone question.
- Ensures coherent responses in multi-turn conversations.

### RAG Chain Construction
- Assembles the complete chain:
  - Reformulate question if needed.
  - Retrieve context (structured + unstructured).
  - Feed context and question to OpenAI GPT-4.
  - Output a concise, natural language answer.

## 🔧 Tech Stack
- **Neo4j**: Stores structured graph data and vector embeddings.
- **LangChain**: Provides chains and tools to integrate LLMs with databases and retrievers.
- **OpenAI GPT (gpt-4o-mini)**: Performs text transformation, question answering, and entity extraction.
- **Wikipedia**: Used as a sample data source.
- **Pydantic**: Handles structured schema for entity extraction.
- **Python (os, dotenv, typing, etc.)**: Manages I/O, environment, and type hints.

## 💡 Use Case
This project can be adapted for any domain where:
- You want to combine structured knowledge graphs with semantic unstructured search.
- You want context-aware Q&A over data from documents.
- You need multi-turn conversational memory support.

## ✅ Key Features
- **Graph-based reasoning**: Interprets text into nodes and relations.
- **Entity-focused search**: Allows semantic matching of fuzzy or misspelled names.
- **Hybrid RAG**: Blends vector-based and graph-based retrieval.
- **Conversational memory**: Converts follow-up questions into standalone queries.
- **Flexible inputs**: Easily extendable to other document sources beyond Wikipedia.