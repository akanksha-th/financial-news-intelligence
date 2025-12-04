# src/api/app.py
from flask import Flask, request, jsonify
from src.query.entities import extract_entities_from_query
from src.query.expansion import expand_entities_to_assets
from src.query.search import search
from src.query.answer import generate_final_answer
from src.query.query_rewriter import QueryRewriter

app = Flask(__name__)

@app.route("/query", methods=["POST"])
def query_endpoint():
    payload = request.json or {}
    q = payload.get("query", "").strip()
    if not q:
        return jsonify({"error":"missing query"}), 400

    # 1. rewrite step: depending on availability, you can optionally call your query_rewriter
    # skip here because user said they already did rewriting elsewhere or will use OpenAI
    rewriter = QueryRewriter()
    rewritten = rewriter.rewrite(q)

    # 2. extract entities
    entities = extract_entities_from_query(rewritten)

    # 3. expand
    expanded = expand_entities_to_assets(entities)

    # 4. semantic search / rank
    ranked_news = search(rewritten, top_k=10, expanded_symbols=expanded.get("symbols", []))

    # 5. answer generation
    response = generate_final_answer(rewritten, ranked_news, expanded)

    out = {
        "rewritten": rewritten,
        "entities": entities,
        "expanded": expanded,
        "results": response
    }
    return jsonify(out)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
