# src/query/answer.py
"""
Generate final answer. If OPENAI_API_KEY is set, call OpenAI for nicer summaries.
Otherwise, produce a short rule-based summary.
"""

import os, json
from typing import List, Dict, Any

OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
USE_OPENAI = bool(OPENAI_KEY)

if USE_OPENAI:
    import openai
    openai.api_key = OPENAI_KEY

def local_summarize_top(news_meta: List[Dict], expanded_symbols: List[str]) -> str:
    # Simple rule-based summary: top headlines + impacted assets
    if not news_meta:
        return "No relevant news found for the query."
    top = news_meta[:3]
    parts = []
    for n in top:
        title = n["meta"].get("title") or n["meta"].get("headline") or n["meta"].get("text")[:140]
        parts.append(f"- {title}")
    assets = ", ".join(expanded_symbols) if expanded_symbols else "no specific tickers"
    return f"Top news:\n" + "\n".join(parts) + f"\nImpacted assets (expanded): {assets}"

def generate_final_answer(query: str, ranked_news: List[Dict], expanded_assets: Dict) -> Dict[str, Any]:
    """
    Returns structured output:
    {
      "answer": "...",
      "top_news": [...],
      "expanded_assets": {...}
    }
    """
    # Build payload
    top_meta = ranked_news[:5]
    expanded_symbols = expanded_assets.get("symbols", [])

    if USE_OPENAI:
        prompt_parts = [
            f"User query: {query}",
            "Top N news (json list):",
            json.dumps([r["meta"] for r in top_meta], ensure_ascii=False),
            f"Expanded assets: {json.dumps(expanded_assets, ensure_ascii=False)}",
            "Write a short concise answer (3-4 sentences) summarizing the top news and why the assets are impacted."
        ]
        prompt = "\n\n".join(prompt_parts)
        try:
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[{"role":"user","content":prompt}],
                max_tokens=200,
                temperature=0.0
            )
            text = resp["choices"][0]["message"]["content"].strip()
            return {"answer": text, "top_news": [r["meta"] for r in top_meta], "expanded_assets": expanded_assets}
        except Exception as e:
            # fallback
            return {"answer": local_summarize_top(top_meta, expanded_symbols), "top_news": [r["meta"] for r in top_meta], "expanded_assets": expanded_assets}
    else:
        return {"answer": local_summarize_top(top_meta, expanded_symbols), "top_news": [r["meta"] for r in top_meta], "expanded_assets": expanded_assets}
