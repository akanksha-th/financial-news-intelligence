from src.agents import (
    build_ingestion_graph, build_dedup_graph, 
    build_entity_graph, build_impact_mapping_graph
)
from langgraph.graph import StateGraph, END
from typing import TypedDict, Dict, Any, List
from IPython.display import Image, display
import os, time


class PipelineState(TypedDict):
    rss_feeds: List
    info: Dict[str, Any]

def retry(times=3):
    def decorator(fn):
        def wrapper(state):
            for attempt in range(times):
                try:
                    return fn(state)
                except Exception as e:
                    print(f"[WARN] {fn.__name__} failed (attempt {attempt+1}: {e})")
                    time.sleep(2)
            raise RuntimeError(f"Node {fn.__name__} failed after {times} retries")
        return wrapper
    return decorator

@retry(times=3)
def run_ingestion(state: PipelineState) -> PipelineState:
    """Runs ingestion agent"""
    ingestion_app = build_ingestion_graph()
    result = ingestion_app.invoke({
        "rss_feeds": state["rss_feeds"],
        "raw_articles": [],
        "standardized_articles": [],
        "saved_count": 0
    })
    state["info"]["ingestion"] = result
    return state

@retry(times=3)
def run_deduplication(state: PipelineState) -> PipelineState:
    """Runs deduplication agent"""
    dedup_app = build_dedup_graph()
    result = dedup_app.invoke({
        "raw_articles": state["info"]["ingestion"]["raw_articles"],
        "embeddings": None,
        "clusters": [],
        "unique_stories": []
    })
    state["info"]["dedup"] = result
    return state

@retry(times=3)
def run_entity_extraction(state: PipelineState) -> PipelineState:
    """Run entity extraction agent"""
    ner_app = build_entity_graph()
    result = ner_app.invoke({
        "stories": state["info"]["dedup"]["unique_stories"],
        "ner_result": [],
        "extended_ner": [],
        "saved_count": 0
    })
    state["info"]["ner"] = result
    return state

@retry(times=3)
def run_impact_mapping(state: PipelineState) -> PipelineState:
    """Run impact mapping agent"""
    impact_app = build_impact_mapping_graph()
    result = impact_app.invoke({
        "entities": state["info"]["ner"]["extended_ner"],
        "computed_impacts": [],
        "saved_count": 0
    })
    state["info"]["impact"] = result
    return state

def build_end_to_end_pipeline():
    graph = StateGraph(PipelineState)

    graph.add_node("ingestion", run_ingestion)
    graph.add_node("deduplication", run_deduplication)
    graph.add_node("entity_extraction", run_entity_extraction)
    graph.add_node("impact_mapping", run_impact_mapping)

    graph.set_entry_point("ingestion")
    graph.add_edge("ingestion", "deduplication")
    graph.add_edge("deduplication", "entity_extraction")
    graph.add_edge("entity_extraction", "impact_mapping")
    graph.add_edge("impact_mapping", END)

    return graph.compile()

if __name__ == "__main__":
    # run on CLI using "python -m src.pipelines.linear_pipeline"

    pipeline = build_end_to_end_pipeline()

    img_bytes = pipeline.get_graph().draw_mermaid_png()
    os.makedirs("graph_images", exist_ok=True)
    output_path = "graph_images/linear_pipeline_graph.png"

    with open(output_path, 'wb') as f:
        f.write(img_bytes)
    print(f"Graph saved successfully at {output_path}")

    result = pipeline.invoke({
        "rss_feeds": [
            "https://www.marketbeat.com/feed/",
            "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
            "https://www.etnownews.com/feeds/gns-etn-companies.xml",
            "https://www.cnbctv18.com/commonfeeds/v1/cne/rss/business.xml"
        ],
        "info": {}
    })

    print("Pipeline Completed")