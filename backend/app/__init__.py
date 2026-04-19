import os
from flask import Flask
from app.config import Config
from app.extensions import db, jwt, CORS


def create_app(config_class=Config):
    flask_app = Flask(__name__)
    flask_app.config.from_object(config_class)

    db.init_app(flask_app)
    jwt.init_app(flask_app)
    CORS(flask_app, resources={r"/api/*": {"origins": "*"}})

    os.makedirs(flask_app.config["UPLOAD_FOLDER"], exist_ok=True)

    from app.api.auth import auth_bp
    from app.api.documents import documents_bp
    from app.api.queries import queries_bp
    from app.api.analytics import analytics_bp
    from app.api.system import system_bp

    flask_app.register_blueprint(auth_bp, url_prefix="/api/auth")
    flask_app.register_blueprint(documents_bp, url_prefix="/api/documents")
    flask_app.register_blueprint(queries_bp, url_prefix="/api/queries")
    flask_app.register_blueprint(analytics_bp, url_prefix="/api/analytics")
    flask_app.register_blueprint(system_bp, url_prefix="/api/system")

    @flask_app.route("/api/health")
    def health():
        return {"status": "ok", "message": "Citation-Grounded LLM API is running"}

    with flask_app.app_context():
        import app.models  # noqa: F401
        db.create_all()

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return {"error": "Token has expired"}, 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return {"error": "Invalid token"}, 401

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return {"error": "Authorization token is missing"}, 401

    return flask_app
