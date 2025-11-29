from typing import TypedDict, List, Dict
import feedparser, re, os
from langgraph.graph import StateGraph, START, END
from src.core.database import insert_raw_articles
from IPython.display import display, Image


class IngestionState(TypedDict):
    rss_feeds: List[str]
    raw_articles: List[Dict]
    standardized_articles: List[Dict]
    saved_count: str


def fetch_rss(state: IngestionState) -> IngestionState:
    """This fetches raw articles from a list of different rss feeds."""
    articles = []
    for feed in state["rss_feeds"]:
        parsed = feedparser.parse(feed)
        for entry in parsed.entries:
            articles.append({
                "source": feed,
                "url": entry.link,
                "title": entry.title,
                "content": getattr(entry, "summary", ""),
                "published_at": getattr(entry, "published", None)
            })

    state["raw_articles"] = articles
    print(f"[Ingestion Agent] Fetched {len(articles)} raw articles from RSS feeds.")
    return state

def clean_text(text):
    """Removes extra whitespace from text."""
    return re.sub(r"\s+", " ", text or "").strip()

def standardize_article(state: IngestionState) -> IngestionState:
    """Cleans and standardtizes raw text in the articles."""
    cleaned = []
    for a in state["raw_articles"]:
        cleaned.append({
            "source": a["source"],
            "url": a["url"],
            "title": clean_text(a["title"]),
            "content": clean_text(a["content"]),
            "published_at": a["published_at"],
        })

    state["standardized_articles"] = cleaned
    print(f"[Ingestion Agent] Standardized {len(cleaned)} articles.")
    return state

def save_to_db(state: IngestionState) -> IngestionState:
    """Saves all the standardized articles to the Postgres database."""
    count = 0
    for article in state["standardized_articles"]:
        try:
            insert_raw_articles(article)
            count += 1
        except Exception as e:
            print(f"[Ingestion Agent] Failed to insert article {article['url']}: {e}")
            break

    state["saved_count"] = count
    print(f"[Ingestion Agent] Saved {count} articles to the database.")

    return state

def build_ingestion_graph() -> StateGraph:
    graph = StateGraph(IngestionState)

    graph.add_node("fetch_rss", fetch_rss)
    graph.add_node("standardize_article", standardize_article)
    graph.add_node("save_to_db", save_to_db)

    graph.add_edge(START, "fetch_rss")
    graph.add_edge("fetch_rss", "standardize_article")
    graph.add_edge("standardize_article", "save_to_db")
    graph.add_edge("save_to_db", END)

    return graph.compile()


if __name__ == "__main__":
    # run on CLI using "python -m src.agents.ingestion_agent"
    rss_feeds = [
        "https://www.marketbeat.com/feed/", 
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms", 
        "https://www.etnownews.com/feeds/gns-etn-companies.xml", 
        "https://www.cnbctv18.com/commonfeeds/v1/cne/rss/business.xml", 
        ]
    
    ingestion_app = build_ingestion_graph()

    result = ingestion_app.invoke({
        "rss_feeds": rss_feeds,
        "raw_articles": [],
        "standardized_articles": [],
        "saved_count": 0
    })

    img_bytes = ingestion_app.get_graph().draw_mermaid_png()
    os.makedirs("graph_images", exist_ok=True)
    output_path = "graph_images/ingestion_graph.png"

    with open(output_path, "wb") as f:
        f.write(img_bytes)
    print(f"Graph saved to: {output_path}")