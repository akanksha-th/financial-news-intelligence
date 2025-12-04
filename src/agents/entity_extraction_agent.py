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

# -----Helper functions-----
def _clean_subword_tokens(token_str: str) -> str:
    """
    If NER left merged strings like '##E' or 'Hyun ##dai' this attempts to reconstruct.
    Input may already be a full string; if it's tokenized into wordpiece artifacts,
    this tries to remove '##' fragments sensibly.
    """
    if not token_str:
        return token_str
    # If token contains '##' pieces or multiple spaces, fix naively:
    # e.g. "Hyun ##dai Motor" -> "Hyundai Motor"
    parts = token_str.split()
    out_parts = []
    for p in parts:
        if p.startswith("##"):
            if out_parts:
                out_parts[-1] = out_parts[-1] + p[2:]
            else:
                # leading ##, just append cleaned
                out_parts.append(p[2:])
        else:
            out_parts.append(p)
    return " ".join(out_parts).strip()

def _normalize_entity_list(lst):
    """Normalize list of strings: strip, lower optionally, remove wordpiece artifacts and duplicates"""
    seen = set()
    out = []
    for v in (lst or []):
        if not isinstance(v, str):
            continue
        cleaned = _clean_subword_tokens(v).strip()
        if not cleaned:
            continue
        # keep original casing for gazetteer matching, but strip duplicates using lower-case
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(cleaned)
    return out

def apply_rules_and_merge(state: EntityExtractionAgent) -> EntityExtractionAgent:
    extended_ents = []
    for item in state["ner_results"]:
        text = item["text"]
        ner_out = item["ner"]

        rules = match_rules(text)
        cleaned = postprocess_entities(ner_out, rules)
        if not isinstance(cleaned, dict):
            cleaned = {}

        # inject story metadata so insert_entities gets story_id, article_ids and article_title
        cleaned["story_id"] = item.get("story_id")
        cleaned["article_ids"] = item.get("article_ids")
        cleaned["article_title"] = item.get("title")

        # Normalize lists and clean tokens (remove '##' etc)
        for k in ["companies", "sectors", "people", "indices", "regulators", "policies", "products", "locations", "kpis", "financial_terms"]:
            cleaned[k] = _normalize_entity_list(cleaned.get(k, []))

        extended_ents.append(cleaned)

    state["extended_ner"] = extended_ents
    print(f"[NER Agent] Performed NER extension on {len(extended_ents)} stories")

    return state

def save_entities(state: EntityExtractionAgent) -> EntityExtractionAgent:
    create_news_entities_table()
    count = 0
    for row in state["extended_ner"]:
        try:
            # defensive: ensure keys exist and are lists/strings as expected by insert_entities
            row_payload = {
                "story_id": row.get("story_id"),
                "article_ids": row.get("article_ids"),
                "article_title": row.get("article_title"),
                "companies": row.get("companies", []),
                "sectors": row.get("sectors", []),
                "people": row.get("people", []),
                "indices": row.get("indices", []),
                "regulators": row.get("regulators", []),
                "policies": row.get("policies", []),
                "products": row.get("products", []),
                "locations": row.get("locations", []),
                "kpis": row.get("kpis", []),
                "financial_terms": row.get("financial_terms", [])
            }
            insert_entities(row_payload)
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