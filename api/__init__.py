from flask import Flask
from flask_cors import CORS
from flask_toastr import Toastr

#API
from api.auth import auth_api
from api.surveys import surveys_api
from api.mfa import mfa_api
from api.academia import surveys_fill

#ROUTES
from routes.surveys import surveys_routes

def create_app():
    app = Flask(__name__, template_folder="../templates", static_folder="../static")  
    CORS(app)
    Toastr(app)

    # Register API blueprints
    app.register_blueprint(auth_api)
    app.register_blueprint(surveys_api)
    app.register_blueprint(mfa_api)
    app.register_blueprint(surveys_fill)

    # Register route blueprints
    app.register_blueprint(surveys_routes)

    return app