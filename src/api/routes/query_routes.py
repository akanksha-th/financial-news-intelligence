from flask import Blueprint, render_template, request, jsonify

query_bp = Blueprint("query", __name__)

@query_bp.route("/query", methods=["GET"])
def query_page():
    return render_template("query.html")