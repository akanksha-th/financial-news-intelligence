from flask import render_template

def page_not_found(e):
    return render_template("errors/404.html"), 404

def server_error(e):
    return render_template("errors/500.html"), 500