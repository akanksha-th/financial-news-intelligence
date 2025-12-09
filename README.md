# Financial News Intelligence System
A modular, end-to-end system that ingests, deduplicates, extracts entities, embeds, indexes and retrieved financial news with context-aware queries and semantic search.

This project is built as a part of a hackathon organized by Tradl.

## **Project Overview**

This repository contains a multi-agent LangGraph pipeline and LLM-powered query system for financial news intelligence. The system focuses on:

    - Ingestion → Deduplication → Entity Extraction → Impact Mapping → Embedding → Retrieval

    - Query rewriting & structured intent extraction

    - Sector-, company-, and regulator-based news retrieval

This project implements a simple, but complete Financial News Intelligence workflow:

1. **Data Ingestion**
    - Fetches raw financial news articles from RSS feeds.
    - Normalizes and stores them in PostgreSQL.
    
2. **Deduplication Pipeline**
    - Combines near duplicate stories.
    - Ensures that only unique stories are stored.

3. **Entity Extraction Agent**
    - Multi-stage NER workflow:
        - Regex based
        - Rule based extraction
        - Gazetteer based fuzzy matching
        - NER using a HuggingFace model
    - Extracts companies, sectors, regulators, policies, indicies.
    - Stores entities in PostgreSQL.

4. **Impact Mapping Pipeline**
    - Loads all entity extraction results.
    - Applies mapping dictionaries (json format).
    - Produces impacted companies/sectors with confidence scores.

5. **Context aware Querying System**
    - Embedding + Semantic Index
        - Uses SentenceTransformers (all-MiniLM) to generate embeddings.
        - Stores vectors in FAISS index.
        - Index saved and reloaded by retriever.

    - Retriever Engine
        - Restrieves stories using 
            - symbol -> company news
            - sector -> matched news
            - regulator -> mpped sector news
            - semantic search using embeddings
            - merged + deduped + scored results

    - Query Understanding System
        - Uses GPT4All (Phi-2 Q4_0 GGUF) for offline rewriting.
        - Extracts query type, entities, and time horizons.
        - Outputs a structured query dict.

6. **Flask API**
    - Simple frontend for running pipeline in real-time and query search.
    - Accepts user queries and passes them to the "Query Agent"
    - Returns ranked results with titles, summaries and scores.

## **Architecture**

         ┌────────────────┐
         │   INGESTION    │
         └───────┬────────┘
                 ▼
      ┌─────────────────────┐
      │  DEDUPLICATION AGENT│
      └────────┬────────────┘
               ▼
     ┌──────────────────────┐
     │ ENTITY EXTRACTION    │
     └────────┬─────────────┘
              ▼
     ┌──────────────────────┐
     │ IMPACT MAPPING AGENT │
     └────────┬─────────────┘
              ▼
     ┌──────────────────────┐
     │   EMBEDDING INDEX    │
     └────────┬─────────────┘
              ▼
     ┌──────────────────────┐
     │     RETRIEVER        │
     └────────┬─────────────┘
              ▼
       ┌─────────────┐
       │ QUERY SYSTEM│
       └─────────────┘

## **Tech Stack**
    Python 3.11

    LangGraph — agent orchestration

    SentenceTransformers + FAISS — embeddings + semantic search

    GPT4All (Phi-2) — offline LLM query rewriting

    RapidFuzz — fuzzy entity matching

    PostgreSQL and SQLite3 — story + entity + impact storage

    psycopg2 — DB access

    Flask — basic query UI

    JSON Rule Library — impact mapping logic

## **Running the Project**

1. Create a virtual environment
```
python -m venv .env
.env\Scripts\activate # (on Windows)
```

2. Install dependencies
```
pip install -r requirements.txt
```

3. Run the agents individually (optional)
```
python -m src.agents.{agent_name}
python -m src.query_system.query_agent
python -m src.core.build_embeddings
```

4. Run the backend pipeline
```
python -m src.pipelines.linear_pipeline
```

5. Run the flask app
```
python run.py
```

## **Post-Hackathon Update**

_The official hackathon submission deadline was December 4th. At the time of submission, several components of the system, including UI and the final unified retrieval flow were incomplete._
_The remaining components have now been implemented after the deadline to bring the project to a functional and well-structured state._