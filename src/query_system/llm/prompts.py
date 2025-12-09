QUERY_REWRITE_PROMPT = """
You are an expert financial news query rewriter.

Rewrite the following user query into a precise, unambiguous
financial search query.

User Query: "{query}"

Rewritten:
"""

STRUCTURED_QUERY_PROMPT = """
Extract structured financial intent from the user query.

Return ONLY valid JSON in this format:

{{
  "rewritten": "...",
  "query_type": "company | sector | regulator | index | policy | unknown",
  "entities": ["..."],
  "time_horizon": "short | medium | long"
}}

User Query: "{query}"
JSON:
"""
