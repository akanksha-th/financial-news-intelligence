import psycopg2, os, json
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


# ==========================================
# NER Agent Utilities
# ==========================================

def fetch_unique_stories(limit: int = None):
    """Fetch deduplicated stories from unique_news"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        sql = "SELECT id, article_ids, article_title, combined_text, num_articles FROM unique_news ORDER BY id;"
        if limit:
            sql += f" LIMIT {limit}"
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
    return rows

def create_news_entities_table():
    """Creates table to store extracted entities."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """ 
            CREATE TABLE IF NOT EXISTS news_entities (
            id SERIAL PRIMARY KEY,
            story_id INT,
            article_ids TEXT,
            article_title TEXT,
            companies TEXT,
            sectors TEXT,
            people TEXT,
            indices TEXT,
            regulators TEXT,
            policies TEXT,
            products TEXT,
            locations TEXT,
            kpis TEXT,
            financial_terms TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )

        conn.commit()
        cur.close()

def insert_entities(entity_row: dict):
    """
    entity_row:
    {
      'story_id': int,
      'article_ids': str (or list),
      'article_title': str,
      'companies': list,
      'sectors': list,
      ...
    }
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO news_entities 
            (story_id, article_ids, article_title, companies, sectors, people, indices, regulators, policies, products, locations, kpis, financial_terms)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                entity_row.get("story_id"),
                json.dumps(entity_row.get("article_ids")),
                entity_row.get("article_title"),
                json.dumps(entity_row.get("companies", [])),
                json.dumps(entity_row.get("sectors", [])),
                json.dumps(entity_row.get("people", [])),
                json.dumps(entity_row.get("indices", [])),
                json.dumps(entity_row.get("regulators", [])),
                json.dumps(entity_row.get("policies", [])),
                json.dumps(entity_row.get("products", [])),
                json.dumps(entity_row.get("locations", [])),
                json.dumps(entity_row.get("kpis", [])),
                json.dumps(entity_row.get("financial_terms", [])),
            )
        )
        conn.commit()
        cur.close()

# ==========================================
# Impact Mapping Agent Utilities
# ==========================================

def fetch_entities(limit: int = None):
    """Fetch extracted entities from the database"""
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        sql = "SELECT * FROM news_entities ORDER BY id;"
        if limit:
            sql += f" LIMIT {limit}"
        cur.execute(sql)
        row_entities = cur.fetchall()
        cur.close()
    return row_entities