from pathlib import Path

from sqlalchemy import text

from app.db.session import engine


def apply_database_schema() -> None:
    """Apply the SQL view and indexes that SQLAlchemy metadata does not fully express."""

    schema_path = Path(__file__).resolve().parents[2] / "sql" / "schema.sql"
    sql = schema_path.read_text()
    with engine.begin() as connection:
        for statement in [part.strip() for part in sql.split(";") if part.strip()]:
            connection.execute(text(statement))
