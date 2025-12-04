from flask import Flask
import pages, errors

"""
This Flask project has two pages that inherit content and style from a parent template.
"""

def create_app():
    app = Flask(__name__)

    app.register_blueprint(pages.bp)
    app.register_error_handler(404, errors.page_not_found)
    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host='0.0.0.0', port='8000', debug=True)