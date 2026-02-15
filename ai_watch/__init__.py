import os
from pathlib import Path

from flask import Flask

from ai_watch.routes import register_routes
from ai_watch.storage import FileDatabase


def create_app(db_path: str | None = None) -> Flask:
    package_dir = Path(__file__).resolve().parent
    project_dir = package_dir.parent
    app = Flask(
        __name__,
        template_folder=str(project_dir / "templates"),
        static_folder=str(project_dir / "static"),
    )

    env_db_path = os.getenv("AI_WATCH_DB_PATH")
    default_db = project_dir / "data" / "db.json"
    resolved_db_path = Path(db_path) if db_path else Path(env_db_path) if env_db_path else default_db
    app.logger.info("Using database file: %s", resolved_db_path)
    storage = FileDatabase(resolved_db_path)

    app.config["DB"] = storage
    register_routes(app)
    return app
