from flask import Blueprint, render_template, request, jsonify
from src.query_system.query_agent import build_query_agent


query_bp = Blueprint("query", __name__)

@query_bp.route("/query", methods=["GET"])
def query_page():
    return render_template("query.html")


query_agent = build_query_agent()

@query_bp.route("/query", methods=["POST"])
def query_endpoint():
    data = request.get_json()

    if not data or "query" not in data:
        return jsonify({"error": "Missing query field"}), 400
    
    user_query = data["query"]
    result = query_agent.invoke({
        "user_query": user_query,
        "restruc_query": {},
        "mapped_assets": {},
        "retrieved_news": [],
        "context": "",
        "response": ""
    })

    return jsonify({"result": result["response"]})