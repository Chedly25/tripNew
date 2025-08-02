
from flask import Flask
from ..web.routes.main import main_bp
from ..web.routes.auth import auth_bp
from ..web.routes.features import features_bp

def create_app():
    app = Flask(__name__)
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(features_bp)
    return app
