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

    default_db = project_dir / "data" / "db.json"
    storage = FileDatabase(Path(db_path) if db_path else default_db)

    app.config["DB"] = storage
    register_routes(app)
    return app
