from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, END
from sentence_transformers import SentenceTransformer
import faiss, os
from src.core.database import (
    fetch_raw_articles, 
    create_unique_stories_table, 
    insert_unique_stories
)
import numpy as np
from IPython.display import display, Image


class DeDupState(TypedDict):
    raw_articles: List[Dict]
    embeddings: np.ndarray
    clusters: List[List[int]]
    unique_stories: List[Dict]


def load_articles(state: DeDupState) -> DeDupState:
    """Fetches raw articles from the database"""
    rows = state["raw_articles"]
    if rows == []:
        rows = fetch_raw_articles()

    state["raw_articles"] = rows
    print(f"[DeDup Agent] Loaded {len(rows)} raw articles.")

    return state

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
def embed_articles(state: DeDupState) -> DeDupState:
    """Embeds raw articles using sentence-transformer embedding model."""
    texts = [
        f"{a['title']} {a['content']}"
        for a in state["raw_articles"]
    ]
    emb = model.encode(texts, show_progress_bar=True)
    state["embeddings"] = np.array(emb).astype('float32')
    print(f"[DeDup Agent] Generated Embeddings Successfully.")

    return state

def l2_to_cos(d):
    return 1 - (d / 2)

def cluster_articles(state: DeDupState) -> DeDupState:
    """Finds similar storues and cluster them."""
    emb = state["embeddings"]
    dim = emb.shape[1]
    index = faiss.IndexFlatL2(dim)
    index.add(emb)

    distances, indices = index.search(emb, k=7)

    clusters = []
    visited = set()

    for i, neighbors in enumerate(indices):
        if i in visited:
            continue

        cluster = []
        for j, dist in zip(neighbors, distances[i]):
            if l2_to_cos(dist) > 0.80:
                cluster.append(j)
                visited.add(j)
        clusters.append((cluster))

    state["clusters"] = clusters
    print(f"[DeDup Agent] Formed {len(clusters)} unique clusters.")

    return state

def save_stories(state: DeDupState) -> DeDupState:
    """Saves unique stories in the database"""
    create_unique_stories_table()
    
    df = state["raw_articles"]
    clusters = state["clusters"]
    stories = []

    for cluster in clusters:
        articles = [df[i] for i in cluster]
        story = {
            "article_ids": [a["id"] for a in articles],
            "article_title": articles[0]["title"],
            "combined_text": " ".join([a["content"] for a in articles]),
            "num_articles": len(articles),
        }
        stories.append(story)
        insert_unique_stories(story)

    state["unique_stories"] = stories
    print(f"[DeDup Agent] Saved {len(stories)} unique stories.")
    return state

def build_dedup_graph():
    graph = StateGraph(DeDupState)

    graph.add_node("load_articles", load_articles)
    graph.add_node("embed_articles", embed_articles)
    graph.add_node("cluster_articles", cluster_articles)
    graph.add_node("save_stories", save_stories)

    graph.set_entry_point("load_articles")
    graph.add_edge("load_articles", "embed_articles")
    graph.add_edge("embed_articles", "cluster_articles")
    graph.add_edge("cluster_articles", "save_stories")
    graph.add_edge("save_stories", END)
    
    return graph.compile()

if __name__ == "__main__":
    # run on CLI using "python -m src.agents.deduplication_agent"
    deduplication_app = build_dedup_graph()

    result = deduplication_app.invoke({
        "raw_articles": [],
        "embeddings": None,
        "clusters": [],
        "unique_stories": []
    })

    print("Deduplication complete!")
    
    img_bytes = deduplication_app.get_graph().draw_mermaid_png()
    os.makedirs("graph_images", exist_ok=True)
    output_path = "graph_images/deduplication_graph.png"

    with open(output_path, 'wb') as f:
        f.write(img_bytes)
    print(f"Graph saved to: {output_path}")
