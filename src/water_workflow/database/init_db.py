from .base import Base
from . import models  # noqa: F401
from .session import get_engine


def init_database() -> None:
    Base.metadata.create_all(bind=get_engine())


if __name__ == "__main__":
    init_database()
    print("Database tables initialized.")
