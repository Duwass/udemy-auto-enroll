"""
History tracking module using SQLite
"""
import sqlite3
from datetime import datetime
from typing import Optional
from config import DB_PATH


def init_db():
    """Initialize database with history table"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS enrollment_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            course_url TEXT UNIQUE NOT NULL,
            course_name TEXT,
            status TEXT NOT NULL,
            enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            source_url TEXT
        )
    ''')
    conn.commit()
    conn.close()


def is_already_enrolled(course_url: str) -> bool:
    """Check if course was already enrolled"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT id FROM enrollment_history WHERE course_url = ? AND status = "success"',
        (course_url,)
    )
    result = cursor.fetchone()
    conn.close()
    return result is not None


def add_enrollment(
    course_url: str,
    course_name: Optional[str],
    status: str,
    source_url: Optional[str] = None
):
    """Add enrollment record to history"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO enrollment_history 
            (course_url, course_name, status, enrolled_at, source_url)
            VALUES (?, ?, ?, ?, ?)
        ''', (course_url, course_name, status, datetime.now(), source_url))
        conn.commit()
    finally:
        conn.close()


def get_history(limit: int = 50) -> list:
    """Get enrollment history"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT course_name, course_url, status, enrolled_at 
        FROM enrollment_history 
        ORDER BY enrolled_at DESC
        LIMIT ?
    ''', (limit,))
    results = cursor.fetchall()
    conn.close()
    return results


# Initialize DB on import
init_db()
