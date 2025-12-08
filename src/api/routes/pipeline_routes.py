from flask import (
    Blueprint, render_template, 
    Response, jsonify, stream_with_context
)
from src.pipelines import build_end_to_end_pipeline
from datetime import datetime
import threading, yaml

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
def run_pipeline_stream():
    yield "event: message\ndata: Starting pipeline...\n\n"

    pipeline = build_end_to_end_pipeline()

    try:
        yield "event: message\ndata: Loading rss_feeds.yaml...\n\n"

        with open("rss_feeds.yaml", "r") as f:
            rss_feeds = yaml.safe_load(f)

        init_state = {
            "rss_feeds": rss_feeds,
            "info": {}
        }
        yield "event: message\ndata: RSS feeds loaded. Starting Ingestion...\n\n"
    
    except Exception as e:
        yield f"event: error\ndata: Failed to load RSS feeds: {e}\n\n"
        return

    # run pipeline and stream messages after each node
    try:
        final_state = pipeline.invoke(init_state)

        PIPELINE_STATE["last_run_time"] = datetime.utcnow().isoformat()
        PIPELINE_STATE["last_status"] = "success"
        PIPELINE_STATE["last_error"] = None

        yield "event: message\ndata: Pipeline completed successfully.\n\n"
        yield f"event: done\ndata: {final_state}\n\n"
    except Exception as e:
        PIPELINE_STATE["last_run_time"] = datetime.utcnow().isoformat()
        PIPELINE_STATE["last_status"] = "error"
        PIPELINE_STATE["last_error"] = str(e)

        yield f"event: error\ndata: Pipeline error: {e}\n\n"


@pipeline_bp.route("/pipeline/run/stream", methods=["GET"])
def pipeline_stream():
    return Response(stream_with_context(run_pipeline_stream()), mimetype="text/event-stream")