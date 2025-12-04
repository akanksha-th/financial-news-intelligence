from flask import Blueprint, render_template

# Blueprints are modules that contain related views that you can conveniently import in __init__.py
bp = Blueprint("pages", __name__)


"""
By default, Flask expects all templates to be in a templates/ directory. 
Therefore, there's no need to include templates/ in the path of the templates.
"""

@bp.route('/')   # <- called a 'view'. In this case, 'home view'
def home():
    return render_template("pages/home.html")

@bp.route("/about")
def about():
    return render_template("pages/about.html")


# if __name__ == "__main__":
#     app.run(host='0.0.0.0', port=8000, debug=True)