import psycopg2, os
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "dbuser": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
}


@contextmanager
def get_db_connection():
    conn = psycopg2.connect(
        dbname=DB_CONFIG["dbname"],
        user=DB_CONFIG["dbuser"],
        password=DB_CONFIG["password"],
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
    )
    try:
        yield conn
    finally:
        conn.close()

def create_table():
    with get_db_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS raw_news (
                id SERIAL PRIMARY KEY,
                source TEXT,
                url TEXT UNIQUE,
                title TEXT,
                content TEXT,
                published_at TEXT
            );
            """
            )
        
        conn.commit()
        cur.close()

def insert_raw_articles(article: Dict):
    with get_db_connection() as conn:
        create_table()
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO raw_news (source, url, title, content, published_at)
            VALUES (%s, %s, %s, %s, %s)
            """, 
            (
                article["source"],
                article["url"],
                article["title"],
                article["content"],
                article["published_at"]
            ),
        )
        
        conn.commit()
        cur.close()
