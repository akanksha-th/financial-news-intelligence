from typing import TypedDict, List, Dict
import os
from langgraph.graph import StateGraph, START, END
from src.core import (
    fetch_unique_stories, create_news_entities_table, insert_entities
)
from src.utils import (
    load_local_or_download, match_rules, postprocess_entities
)


class EntityExtractionAgent(TypedDict):
    stories: List[Dict]
    ner_results: List[Dict]
    extended_ner: List[Dict]
    saved_count: int


def fetch_stories(state: EntityExtractionAgent) -> EntityExtractionAgent:
    """Fetches stories from the database"""
    stories = fetch_unique_stories(limit=None)
    state["stories"] = stories
    print(f"[NER Agent] Loaded {len(stories)} unique stories.")
    return state

model_local_dir = "./data/models/dslim-bert-base-ner"
model_name = "dslim/bert-base-NER"

def run_ner_on_stories(state: EntityExtractionAgent) -> EntityExtractionAgent:
    ner = load_local_or_download(model_name, model_local_dir, task="ner")
    results = []
    for s in state["stories"]:
        text = s.get("combined_text")

        if len(text) > 3000: # Chunking
            chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]
        else:
            chunks = [text]
        entities = []
        for c in chunks:
            try:
                chunk_out = ner(c)
                if chunk_out:
                    entities.extend(chunk_out)

            except Exception as e:
                print(f"[NER Agent] Chunk failed: {e}")
        results.append({
            "story_id": s["id"],
            "title": s.get("article_title"),
            "article_ids": s.get("article_ids"),
            "ner": entities,
            "text": text
            })
    state["ner_results"] = results
    print(f"[NER Agent] Completed NER on {len(results)} stories")
    return state

def apply_rules_and_merge(state: EntityExtractionAgent) -> EntityExtractionAgent:
    extended_ents = []
    for item in state["ner_results"]:
        text = item["text"]
        ner_out = item["ner"]

        rules = match_rules(text)
        cleaned = postprocess_entities(ner_out, rules)
        extended_ents.append(cleaned)

    state["extended_ner"] = extended_ents
    print(f"[NER Agent] Performed NER extension on {len(extended_ents)} stories")

    return state

def save_entities(state: EntityExtractionAgent) -> EntityExtractionAgent:
    create_news_entities_table()
    count = 0
    for row in state["extended_ner"]:
        try:
            insert_entities(row)
            count += 1
        except Exception as e:
            print(f"[Ingestion Agent] Failed to insert: {e}")
    
    state["saved_count"] = count
    print(f"[NER Agent] Saved {count} entity rows.")
    return state


def build_entity_graph():
    graph = StateGraph(EntityExtractionAgent)

    graph.add_node("fetch_stories", fetch_stories)
    graph.add_node("run_ner", run_ner_on_stories)
    graph.add_node("extended_ner", apply_rules_and_merge)
    graph.add_node("save_entities", save_entities)

    graph.set_entry_point("fetch_stories")
    graph.add_edge("fetch_stories", "run_ner")
    graph.add_edge("run_ner", "extended_ner")
    graph.add_edge("extended_ner", "save_entities")
    graph.add_edge("save_entities", END)

    return graph.compile()


if __name__ == "__main__":
    # run on CLI using "python -m src.agents.entity_extraction_agent"
    ner_app = build_entity_graph()
    result = ner_app.invoke({
        "stories": [],
        "ner_results": [],
        "extended_ner": [],
        "saved_count": 0
    })

    img_bytes = ner_app.get_graph().draw_mermaid_png()
    os.makedirs("graph_images", exist_ok=True)
    output_path = "graph_images/entity_extraction_graph.png"

    with open(output_path, "wb") as f:
        f.write(img_bytes)
    print(f"Graph saved to: {output_path}")