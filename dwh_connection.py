import os
from functools import lru_cache

from sqlalchemy import create_engine


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATABASE_URL = "postgresql+psycopg2://dataeng:dataeng123@localhost:5432/dwh"
DEFAULT_SQLITE_URL = "sqlite:///" + os.path.join(BASE_DIR, "database", "retail_dwh.db").replace("\\", "/")


def default_database_url():
    return "postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}".format(
        user=os.getenv("PGUSER", "dataeng"),
        password=os.getenv("PGPASSWORD", "dataeng123"),
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        database=os.getenv("PGDATABASE", "dwh")
    )


@lru_cache(maxsize=4)
def get_engine(database_url=None):
    database_url = database_url or os.getenv("DWH_DATABASE_URL") or default_database_url()
    return create_engine(database_url, pool_pre_ping=True)
