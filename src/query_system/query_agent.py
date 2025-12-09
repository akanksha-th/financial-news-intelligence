from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, START, END
from .llm.processor import QueryProcessor
from .search.retriever import Retriever

class QueryState(TypedDict):
    user_query: str
    restruc_query: Dict
    mapped_assets: Dict
    retrieved_news: List[Dict]
    context: str
    response: str

processor = QueryProcessor()
def understand_query(state: QueryState) -> QueryState:
    """
    Takes raw  user query and extracts
        - entities mentioned
        - time range
        - query intent
        - sentiment
        - sector/industry
    """
    user_q = state["user_query"]
    structured = processor.process(user_q)
    state["restruc_query"] = structured
    print(f"[Query Agent] Query restructured successfully!")
    return state

retriever = Retriever()
def context_retriever(state: QueryState) -> QueryState:
    """Fetch relevant data from the restructured query"""
    restructured_q = state["restruc_query"]
    mapped_assets = retriever.map_query_to_assets(restructured_q)

    # If embedding index is not loaded, disable semantic retrieval
    use_semantic = retriever.idx is not None

    news = retriever.get_relevant_news(
        restructured_q,
        mapped_assets,
        top_k=15,
        use_semantic=use_semantic
    )

    state["mapped_assets"] = mapped_assets
    state["retrieved_news"] = news
    print(f"[Query Agent] Retrieved the news from the db.")
    return state

def context_assembler(state: QueryState) -> QueryState:
    """Builds a context window for the LLM"""
    rewritten = state["restruc_query"].get("rewritten")
    entities = state["restruc_query"].get("entities", {})
    query_type = state["restruc_query"].get("query_type")
    time_horizon = state["restruc_query"].get("time_horizon")

    news = state["retrieved_news"]

    context_lines = []
    context_lines.append("### Query Understanding\n")
    context_lines.append(f"- Rewritten Query: {rewritten}")
    context_lines.append(f"- Query Type: {query_type}")
    context_lines.append(f"- Time Horizon: {time_horizon}")
    context_lines.append(f"- Entities Detected: {entities}\n")

    context_lines.append("### Retrieved Relevant Articles:\n")
    for i, item in enumerate(news):
        title = item.get("article_title")
        text  = item.get("combined_text")
        score = item.get("score")

        score = item.get("score", 0.0) or 0.0
        context_lines.append(f"{i+1}. **{title}** (Score: {score:.4f})")
        context_lines.append(f"   {text[:300]}...\n")

    state["context"] = "\n".join(context_lines)
    return state

def answer_generation(state: QueryState) -> QueryState:
    """Produces a clean table of retrieved articles"""

    articles = state["retrieved_news"]

    def wrap_text(text: str, width: int = 80) -> str:
        lines = []
        while len(text) > width:
            lines.append(text[:width])
            text = text[width:]
        lines.append(text)
        return "<br>".join(lines)
    
    table = []
    table.append("| # | Article Title | Summary |  Score  |")
    table.append("|---|---------------|---------|---------|")

    for i, art in enumerate(articles, 1):
        title = art.get("article_title", "Untitled").replace("|", " ")
        text = art.get("combined_text", "").replace("|", " ")
        score = art.get("score", 0.0) or 0.0

        wrapped_summary = wrap_text(text, width=500)

        table.append(f"| {i} | {title} | {wrapped_summary} | {score:.4f} |")

    state["response"] = "\n".join(table)
    print(f"[Query Agent] Relevant News articles are fetched below.")
    return state


def build_query_agent():
    graph = StateGraph(QueryState)

    graph.add_node("understand_query", understand_query)
    graph.add_node("context_retriever", context_retriever)
    graph.add_node("context_assembler", context_assembler)
    graph.add_node("answer_generation", answer_generation)

    graph.add_edge(START, "understand_query")
    graph.add_edge("understand_query", "context_retriever")
    graph.add_edge("context_retriever", "context_assembler")
    graph.add_edge("context_assembler", "answer_generation")
    graph.add_edge("answer_generation", END)

    return graph.compile()


if __name__ == "__main__":
    # run on CLI using "python -m src.query_system.query_agent"

    query_app = build_query_agent()
    query = "HDFC plans for the next quarter"
    result = query_app.invoke({
        "user_query": query,
        "restruc_query": {},
        "mapped_assets": {},
        "retrieved_docs": [],
        "context": "",
        "response": ""
    })

    print("\nQuery Agent Execution Successful!\n")
    print("Final Response:")
    print(result["response"])