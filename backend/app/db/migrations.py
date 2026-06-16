from app.models.database import Base, engine
from app.core.config import settings


def run_migrations():
    Base.metadata.create_all(bind=engine)
    print(f"[Sydney] Database tables created at {settings.database_url}")


def drop_all():
    Base.metadata.drop_all(bind=engine)
    print("[Sydney] All tables dropped")
