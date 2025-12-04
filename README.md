AI-Powered Financial News Intelligence System

A multi-agent LangGraph pipeline for entity extraction, semantic deduplication, and impact mapping of financial news.

Overview

This project is an end-to-end system that ingests financial news, removes duplicates, extracts structured entities, performs impact mapping, and supports context-aware query interpretation.

The stack is mostly offline and built around LangGraph agents, PostgreSQL, HuggingFace NER, and custom rule-based mapping.
The goal was to build a complete pipeline that can power a financial news intelligence engine.

Project Structure
1. Ingestion + Deduplication

Fetches articles from RSS feeds

Cleans and normalizes text

Uses sentence-transformer embeddings to detect duplicates

Stores unique_stories in the DB

2. Entity Extraction Agent (LangGraph)

Takes deduplicated stories as input

Extracts:

companies

sectors

regulators

indices

policies

products

KPIs

Uses gazetteers + fuzzy matching + NER model

Saves results into news_entities table

3. Impact Mapping Agent (LangGraph)

Loads unprocessed entity rows

Applies impact logic using JSON rule libraries:

company → symbol

sector → symbols

regulator rule → sectors

policy rule → sectors

Computes per-story impacted assets with confidence scores

Saves to story_impacts

This part took the most debugging because of edge cases in mappings, missing tables, and unexpected entity shapes.

4. Query System (Work in Progress)

A context-aware query system was partially implemented.

Completed:

Offline LLM (GPT4All, Phi-2 GGUF) for query rewriting

Structured intent extraction (query type, entities, horizon)

Mapping query → companies / sectors / symbols

Retrieval module:

sector-level retrieval

regulator-rule-based retrieval

semantic search over embeddings

Remaining (not completed before deadline):

Final unified query pipeline end-to-end

Response summarisation layer

Flask API wrapper for serving results

Some mapping inconsistencies (policy → sectors, rare regulator cases)

Tech Stack

Python 3.11

LangGraph (multi-agent orchestration)

PostgreSQL + psycopg2

SentenceTransformers (dedupe + semantic search)

HuggingFace models (entity extraction)

GPT4All (phi-2.Q4_0.gguf) for offline rewriting

RapidFuzz for fuzzy company matching

Custom JSON-based mapping libraries

Challenges Faced

LangGraph node return signatures breaking silently

Table creation order for impact mapping

Missing/null entity fields causing agent crashes

Fuzzy entity extraction producing noisy results

Structuring large mapping dictionaries (company, regulator, policy)

Incomplete query system due to time constraints

GPT4All requiring specific path conventions + no internet fallback

What’s Working End-to-End

✔ RSS ingestion
✔ Deduplication using embeddings
✔ News storage in DB
✔ Entity extraction pipeline (LangGraph agent)
✔ Entity storage (news_entities)
✔ Impact mapping pipeline (LangGraph agent)
✔ Impact storage (story_impacts)
✔ Query rewriting + intent extraction (offline LLM)
✔ Retrieval (sector, regulator, semantic)

What Remains

❌ End-to-end Query → Retrieval → Summarization pipeline
❌ Integrating impact scores into final ranking
❌ Flask API for consumption
❌ A final consumer-facing output format
❌ UI (not required, but useful)

How to Run (short)
python -m src.agents.entity_extraction_agent
python -m src.agents.impact_mapping_agent
python src/llm/rewriter.py
