# server.py

from fastapi import FastAPI, HTTPException, Header
from typing import Optional, Dict, Any
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
import os
import uvicorn
import json

API_KEY = os.getenv("API_KEY", "your-api-key-here")
DB_PATH = Path(__file__).parent / "vigilant.db"
PORT = int(os.getenv("PORT", 8000))

app = FastAPI(title="Vigilant API", version="0.1.0")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Rigs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rigs (
            rig_id TEXT PRIMARY KEY,
            hostname TEXT,
            ip_address TEXT,
            first_seen TEXT,
            last_seen TEXT,
            status TEXT DEFAULT 'offline'
        )
    """)
    
    # Heartbeats table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS heartbeats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rig_id TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            cpu_percent REAL,
            memory_percent REAL,
            disk_percent REAL,
            data TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (rig_id) REFERENCES rigs(rig_id)
        )
    """)
    
    conn.commit()
    conn.close()


# Initialize database on startup
init_db()


def verify_api_key(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization")
    
    key = authorization.replace("Bearer ", "")
    if key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return key


@app.get("/")
def root():
    return {"service": "Vigilant API", "version": "0.1.0", "status": "running"}


@app.post("/api/heartbeat")
def receive_heartbeat(data: Dict[str, Any], authorization: Optional[str] = Header(None)):
    verify_api_key(authorization)
    
    rig_id = data.get("rig_id")
    if not rig_id:
        raise HTTPException(status_code=400, detail="Missing rig_id")
    
    timestamp = data.get("timestamp", datetime.now(timezone.utc).isoformat())
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Update or insert rig
    cursor.execute("SELECT rig_id FROM rigs WHERE rig_id = ?", (rig_id,))
    if cursor.fetchone():
        cursor.execute("""
            UPDATE rigs 
            SET last_seen = ?, status = 'online', hostname = ?, ip_address = ?
            WHERE rig_id = ?
        """, (timestamp, data.get("hostname"), data.get("ip_address"), rig_id))
    else:
        cursor.execute("""
            INSERT INTO rigs (rig_id, hostname, ip_address, first_seen, last_seen, status)
            VALUES (?, ?, ?, ?, ?, 'online')
        """, (rig_id, data.get("hostname"), data.get("ip_address"), timestamp, timestamp))
    
    # Insert heartbeat
    cursor.execute("""
        INSERT INTO heartbeats (rig_id, timestamp, cpu_percent, memory_percent, disk_percent, data)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (rig_id, timestamp, data.get("cpu_percent"), data.get("memory_percent"), 
          data.get("disk_percent"), json.dumps(data)))
    
    conn.commit()
    conn.close()
    
    return {"status": "success", "rig_id": rig_id, "timestamp": timestamp}


@app.get("/api/rigs")
def list_rigs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM rigs")
    rigs = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return {"count": len(rigs), "rigs": rigs}


@app.get("/api/rigs/{rig_id}")
def get_rig(rig_id: str):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM rigs WHERE rig_id = ?", (rig_id,))
    rig = cursor.fetchone()
    
    if not rig:
        conn.close()
        raise HTTPException(status_code=404, detail="Rig not found")
    
    cursor.execute("""
        SELECT * FROM heartbeats 
        WHERE rig_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
    """, (rig_id,))
    latest_heartbeat = cursor.fetchone()
    
    conn.close()
    
    return {
        "rig": dict(rig),
        "latest_heartbeat": dict(latest_heartbeat) if latest_heartbeat else None
    }


if __name__ == "__main__":
    print(f"Starting Vigilant Server on port {PORT}")
    print(f"Database: {DB_PATH}")
    print(f"API Key: {API_KEY}")
    print(f"\nSet API_KEY environment variable to change the API key")
    print(f"Example: API_KEY=mykey python server.py\n")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
