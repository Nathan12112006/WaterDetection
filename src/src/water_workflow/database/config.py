from __future__ import annotations

import os
from functools import lru_cache
from urllib.parse import quote_plus

from dotenv import load_dotenv


@lru_cache(maxsize=1)
def get_database_url() -> str:
    load_dotenv()
    explicit_url = os.getenv("DATABASE_URL")
    if explicit_url:
        return explicit_url
    values = {
        "MYSQL_DATABASE": os.getenv("MYSQL_DATABASE"),
        "MYSQL_USER": os.getenv("MYSQL_USER"),
        "MYSQL_PASSWORD": os.getenv("MYSQL_PASSWORD"),
    }
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise RuntimeError("Set DATABASE_URL or: " + ", ".join(missing))
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_HOST_PORT", "3307")
    return f"mysql+pymysql://{quote_plus(values['MYSQL_USER'])}:{quote_plus(values['MYSQL_PASSWORD'])}@{host}:{port}/{values['MYSQL_DATABASE']}?charset=utf8mb4"
