from flask import Blueprint, jsonify
from datetime import datetime
from src.api.routes.pipeline_routes import PIPELINE_STATE

system_bp = Blueprint("system", __name__)

# ----- health check -----
@system_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200

# ----- api version -----
@system_bp.route("/version", methods=["GET"])
def version():
    return jsonify({
        "version": "1.0.0",
        "description": "Financial News Intelligence API",
        "last_updated": "2025-01-01"
    })

# ----- pipeline status -----
@system_bp.route("/pipeline/status", methods=["GET"])
def pipeline_status():
    return jsonify(PIPELINE_STATE), 200

# ----- current server time -----
@system_bp.route("/system/time", methods=["GET"])
def server_time():
    return jsonify({
        "server_time_utc": datetime.utcnow().isoformat()
    })