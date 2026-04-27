import sqlite3
import json
import os
import time

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "history.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS estimates (
            id TEXT PRIMARY KEY,
            timestamp REAL,
            filename TEXT,
            report_json TEXT,
            file_path TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS market_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp REAL,
            metal TEXT,
            price_usd REAL,
            exchange_rate REAL
        )
    ''')
    conn.commit()
    conn.close()

def save_estimate(estimate_id, filename, report_data, file_path):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO estimates (id, timestamp, filename, report_json, file_path)
        VALUES (?, ?, ?, ?, ?)
    ''', (estimate_id, time.time(), filename, json.dumps(report_data), file_path))
    conn.commit()
    conn.close()

def get_history(limit=20):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT id, timestamp, filename, report_json FROM estimates ORDER BY timestamp DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    history = []
    for row in rows:
        history.append({
            "id": row["id"],
            "timestamp": row["timestamp"],
            "filename": row["filename"],
            "report": json.loads(row["report_json"])
        })
    return history

def delete_estimate(estimate_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get file path to delete actual file too
    cursor.execute('SELECT file_path FROM estimates WHERE id = ?', (estimate_id,))
    row = cursor.fetchone()
    if row and row[0] and os.path.exists(row[0]):
        try:
            os.remove(row[0])
        except Exception:
            pass
            
    cursor.execute('DELETE FROM estimates WHERE id = ?', (estimate_id,))
    conn.commit()
    conn.close()

def save_market_snapshot(metal, price_usd, exchange_rate):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO market_history (timestamp, metal, price_usd, exchange_rate)
        VALUES (?, ?, ?, ?)
    ''', (time.time(), metal, price_usd, exchange_rate))
    conn.commit()
    conn.close()

def get_market_history(limit=100):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute('SELECT timestamp, metal, price_usd, exchange_rate FROM market_history WHERE price_usd > 0 ORDER BY timestamp DESC LIMIT ?', (limit,))
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]

# Initial initialization
init_db()
