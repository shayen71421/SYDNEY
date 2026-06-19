from app.models.database import Base, engine
from app.core.config import settings
from sqlalchemy import text


def run_migrations():
    Base.metadata.create_all(bind=engine)
    _add_missing_columns()
    print(f"[Sydney] Database tables created at {settings.database_url}")


def _add_missing_columns():
    with engine.connect() as conn:
        dialect = engine.dialect.name
        if dialect == "sqlite":
            _add_column_sqlite(conn, "reports", "clinvar_review_strength", "FLOAT DEFAULT 0.0")
            _add_column_sqlite(conn, "variants", "why_matters", "TEXT")
            _add_column_sqlite(conn, "variants", "gnomad_af", "FLOAT")
            _add_column_sqlite(conn, "variants", "gnomad_data", "JSON")


def _add_column_sqlite(conn, table: str, column: str, col_type: str):
    try:
        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
        conn.commit()
    except Exception:
        pass  # Column already exists


def drop_all():
    Base.metadata.drop_all(bind=engine)
    print("[Sydney] All tables dropped")
