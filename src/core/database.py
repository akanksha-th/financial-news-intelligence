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


# ==========================================
# Ingestion Agent Utilities
# ==========================================

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


# ==========================================
# DeDuplication Agent Utilities
# ==========================================

def fetch_raw_articles():
    """Fetches raw articles from the raw_news table for deduplication"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute(
            """
            SELECT id, title, content from raw_news ORDER BY id;
            """
        )
        rows = cur.fetchall()
        cur.close()
    return rows

def create_unique_stories_table():
    """Creates a new table to store dedupicated news stories"""
    with get_db_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS unique_news (
                id SERIAL PRIMARY KEY,
                article_ids TEXT,
                article_title TEXT,
                combined_text TEXT,
                num_articles INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """
        )

        conn.commit()
        cur.close()

def insert_unique_stories(story: Dict):
    """
    story = {
        'article_ids': [...],
        'article'_title': str,
        'combined_text': str,
        'num_articles': int
    """
    with get_db_connection() as conn:
        cur = conn.cursor()

        cur.execute(
            """
            INSERT INTO unique_news (article_ids, article_title, combined_text, num_articles)
            VALUES (%s, %s, %s, %s)
            """, 
            (
                str(story["article_ids"]),
                story["article_title"],
                story["combined_text"],
                story["num_articles"],
            ),
        )
        
        conn.commit()
        cur.close()