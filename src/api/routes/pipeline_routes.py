from flask import Blueprint, render_template, request, jsonify
from src.pipelines import build_end_to_end_pipeline
from datetime import datetime
import threading

pipeline_bp = Blueprint("pipeline", __name__)

PIPELINE_STATE = {
    "last_run_time": None,
    "last_status": None,
    "last_error": None
}

@pipeline_bp.route("/pipeline", methods=["GET"])
def pipeline_page():
    return render_template(
        "pipeline.html",
        status=PIPELINE_STATE)


# ------Run Pipeline -------
def run_pipeline_background():
    """Runs in a background thread so browser does not freeze"""
    try:
        app = build_end_to_end_pipeline()
        app.invoke({})

        PIPELINE_STATE["last_run_time"] = datetime.utcnow().isoformat()
        PIPELINE_STATE["last_status"] ="success"
        PIPELINE_STATE["last_error"] = None

    except Exception as e:
        PIPELINE_STATE["last_run_time"] = datetime.utcnow().isoformat()
        PIPELINE_STATE["last_status"] = "error"
        PIPELINE_STATE["last_error"] = str(e)


@pipeline_bp.route("/pipeline/run", methods=["POST"])
def run_pipeline():
    """Triggers the pipeline in a background thread"""
    t = threading.Thread(target=run_pipeline_background)
    t.start()

    return jsonify({
        "status": "Pipelien started",
        "timestamp": datetime.utcnow().isoformat()
    })