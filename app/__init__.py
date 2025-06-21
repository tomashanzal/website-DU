
from flask import Flask
from flask import request
def create_app():
    app = Flask(__name__)
    app.jinja_env.globals['request'] = request
    from .routes import main
    app.register_blueprint(main)

    return app

