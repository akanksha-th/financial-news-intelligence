from flask import Flask
from .routes.pipeline_routes import pipeline_bp
from .routes.query_routes import query_bp
from .routes.system_routes import system_bp
from .errors import page_not_found, server_error

def create_app():
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )

    app.register_blueprint(pipeline_bp)
    app.register_blueprint(query_bp)
    app.register_blueprint(system_bp)

    app.register_error_handler(404, errors.page_not_found)
    app.register_error_handler(500, errors.server_error)
    
    return app
