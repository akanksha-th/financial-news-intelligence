import psycopg2, os, json
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from typing import Dict, List, Any, Optional
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

def create_story_impacts_table():
    """Create the story_impacts table if not exists."""
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS story_impacts (
                id SERIAL PRIMARY KEY,
                story_id INTEGER NOT NULL,
                impacted_assets TEXT NOT NULL,
                summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

import json

def insert_story_impacts(story_id: int, impacts: list, summary: str = None):
    """
    Insert computed impact mapping results into story_impacts table.
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO story_impacts (story_id, impacted_assets, summary)
            VALUES (%s, %s, %s);
            """,
            (story_id, json.dumps(impacts), summary)
        )
        conn.commit()

def fetch_unprocessed_entities():
    """
    Fetch stories from news_entities that do NOT exist in story_impacts.
    Convert DB rows into clean dictionaries for the agent.
    """
    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("""
            SELECT ne.*
            FROM news_entities ne
            LEFT JOIN story_impacts si
                ON ne.id = si.story_id
            WHERE si.story_id IS NULL;
        """)
        rows = cur.fetchall()

    # Normalize output for agent
    output = []
    for r in rows:
        try:

            def parse_json(x):
                if not x or x == "null":
                    return []
                try:
                    return json.loads(x)
                except:
                    return []

            output.append({
                "story_id": r["id"],   # THIS is the link
                "entities": {
                    "companies": parse_json(r["companies"]),
                    "sectors": parse_json(r["sectors"]),
                    "people": parse_json(r["people"]),
                    "indices": parse_json(r["indices"]),
                    "regulators": parse_json(r["regulators"]),
                    "policies": parse_json(r["policies"]),
                    "products": parse_json(r["products"]),
                    "locations": parse_json(r["locations"]),
                    "kpis": parse_json(r["kpis"]),
                    "financial_terms": parse_json(r["financial_terms"]),
                }
            })

        except Exception as e:
            print("ERROR parsing row:", r, e)

    return output


try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    _HAS_PG = True
except Exception:
    psycopg2 = None
    RealDictCursor = None
    _HAS_PG = False

# ---------------------------------------------------------------------
# Helper: fetch stories by a list of ids, preserving order of ids
# ---------------------------------------------------------------------
def fetch_stories_by_ids(ids: List[int]) -> List[Dict[str, Any]]:
    """
    Returns list of story dicts in the same order as ids.
    Works with Postgres (RealDictCursor) or sqlite3 fallback.
    """
    if not ids:
        return []
    if _HAS_PG:
        sql = "SELECT * FROM unique_news WHERE id = ANY(%s);"
        # Using ANY preserves no order - we'll reorder later
        with get_db_connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(sql, (ids,))
            rows = cur.fetchall()
            cur.close()
        # reorder rows to match ids
        id_to_row = {r["id"]: r for r in rows}
        ordered = [id_to_row.get(i) for i in ids if id_to_row.get(i) is not None]
        return ordered
    else:
        # sqlite fallback: use ? placeholders
        placeholders = ",".join("?" for _ in ids)
        sql = f"SELECT * FROM unique_news WHERE id IN ({placeholders});"
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(sql, ids)
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]
        conn.close()
        id_to_row = {r["id"]: r for r in rows}
        ordered = [id_to_row.get(i) for i in ids if id_to_row.get(i) is not None]
        return ordered

def fetch_stories_by_sector(sector_name: str, limit: Optional[int] = 100) -> List[Dict[str, Any]]:
    sector_norm = sector_name.lower().strip()

    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        sql = """
            SELECT un.*
            FROM unique_news un
            JOIN news_entities ne ON ne.story_id = un.id
            WHERE LOWER(ne.sectors::text) LIKE %s
            ORDER BY un.created_at DESC
            LIMIT %s
        """

        cur.execute(sql, (f"%{sector_norm}%", limit))
        rows = cur.fetchall()
        cur.close()
        return rows

def fetch_all_unique_comp_stories(limit: Optional[int] = None, company_like: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Return all unique stories used for embedding indexing.
    """
    company_norm = company_like.lower().strip()

    with get_db_connection() as conn:
        cur = conn.cursor(cursor_factory=RealDictCursor)

        sql = """
            SELECT un.*
            FROM unique_news un
            JOIN news_entities ne ON ne.story_id = un.id
            WHERE LOWER(ne.companies::text) LIKE %s
            ORDER BY un.created_at DESC
            LIMIT %s
        """

        cur.execute(sql, (f"%{company_norm}%", limit))
        rows = cur.fetchall()
        cur.close()
        return rows