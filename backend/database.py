import sqlite3
import os
from datetime import datetime

HERE = os.path.dirname(__file__)
DB_PATH = os.path.join(HERE, "app.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            label TEXT NOT NULL,
            ai_probability REAL NOT NULL,
            human_probability REAL NOT NULL,
            created_at TEXT NOT NULL,
            batch_id TEXT,
            filename TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()


def create_user(username, email, password_hash):
    conn = get_db()
    conn.execute(
        "INSERT INTO users (username, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (username, email, password_hash, datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def get_user_by_username(username):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    return row


def get_user_by_id(user_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def save_detection(user_id, text, label, ai_prob, human_prob, batch_id=None, filename=None):
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO detections (user_id, text, label, ai_probability, human_probability, "
        "created_at, batch_id, filename) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (user_id, text, label, ai_prob, human_prob, datetime.utcnow().isoformat(), batch_id, filename),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_batch(user_id, batch_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM detections WHERE user_id = ? AND batch_id = ? ORDER BY ai_probability DESC",
        (user_id, batch_id),
    ).fetchall()
    conn.close()
    return rows


def get_history(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM detections WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
    ).fetchall()
    conn.close()
    return rows


def get_detection(detection_id, user_id):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM detections WHERE id = ? AND user_id = ?", (detection_id, user_id)
    ).fetchone()
    conn.close()
    return row
