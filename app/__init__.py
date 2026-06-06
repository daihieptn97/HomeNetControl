from __future__ import annotations

from pathlib import Path

from flask import Flask
from sqlalchemy import text

from .config import Config
from .extensions import db, login_manager, socketio
from .models import RouterConfig, Setting, User
from .routes.api import api_bp
from .routes.auth import auth_bp
from .routes.pages import pages_bp
from .services.background import start_background_tasks
from .services.settings import set_setting


def create_app(config_object: type[Config] | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object or Config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    socketio.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Vui lòng đăng nhập để tiếp tục."

    app.register_blueprint(auth_bp)
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix="/api")

    with app.app_context():
        _configure_sqlite()
        db.create_all()
        _bootstrap_defaults(app)

    start_background_tasks(app)
    return app


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return db.session.get(User, int(user_id))


def _configure_sqlite() -> None:
    if not str(db.engine.url).startswith("sqlite"):
        return
    db.session.execute(text("PRAGMA journal_mode=WAL"))
    db.session.execute(text("PRAGMA busy_timeout=30000"))
    db.session.commit()


def _bootstrap_defaults(app: Flask) -> None:
    username = app.config["ADMIN_USERNAME"]
    user = User.query.filter_by(username=username).first()
    if user is None:
        user = User(username=username)
        user.set_password(app.config["ADMIN_PASSWORD"])
        db.session.add(user)

    if RouterConfig.query.first() is None:
        db.session.add(
            RouterConfig(
                base_url=app.config["ROUTER_URL"],
                username=app.config["ROUTER_USERNAME"],
                password=app.config["ROUTER_PASSWORD"],
            )
        )

    defaults = {
        "network_interface": app.config["NETWORK_INTERFACE"],
        "network_subnet": app.config["NETWORK_SUBNET"],
        "scan_interval_seconds": str(app.config["SCAN_INTERVAL_SECONDS"]),
        "mock_data": "true" if app.config["MOCK_DATA"] else "false",
    }
    for key, value in defaults.items():
        if db.session.get(Setting, key) is None:
            set_setting(key, value, commit=False)

    db.session.commit()
