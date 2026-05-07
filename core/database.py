import sqlite3
import json
import os
from core.models import Circuit

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tableau_elect.db")


def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    conn = _conn()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            circuits TEXT NOT NULL DEFAULT '[]',
            surface INTEGER,
            chambres INTEGER,
            has_pac INTEGER DEFAULT 0,
            has_ve INTEGER DEFAULT 0,
            has_atelier INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def lister_projets():
    conn = _conn()
    rows = conn.execute(
        "SELECT id, name, updated_at FROM projects ORDER BY updated_at DESC"
    ).fetchall()
    conn.close()
    return rows


def load_project(project_id):
    conn = _conn()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    if row is None:
        return None
    circuits = [Circuit(**c) for c in json.loads(row[4])]
    metadata = {
        "surface": row[5],
        "chambres": row[6],
        "has_pac": bool(row[7]) if row[7] else False,
        "has_ve": bool(row[8]) if row[8] else False,
        "has_atelier": bool(row[9]) if row[9] else False,
    }
    return circuits, metadata, row[1]


def save_project(project_id, circuits, name=None, metadata=None):
    conn = _conn()
    circuits_json = json.dumps([vars(c) for c in circuits])
    if name:
        conn.execute(
            "UPDATE projects SET circuits = ?, name = ?, updated_at = datetime('now') WHERE id = ?",
            (circuits_json, name, project_id),
        )
    else:
        conn.execute(
            "UPDATE projects SET circuits = ?, updated_at = datetime('now') WHERE id = ?",
            (circuits_json, project_id),
        )
    if metadata:
        conn.execute(
            """UPDATE projects SET surface = ?, chambres = ?, has_pac = ?, has_ve = ?, has_atelier = ?
               WHERE id = ?""",
            (
                metadata.get("surface"),
                metadata.get("chambres"),
                int(metadata.get("has_pac", False)),
                int(metadata.get("has_ve", False)),
                int(metadata.get("has_atelier", False)),
                project_id,
            ),
        )
    conn.commit()
    conn.close()


def create_project(name="Sans nom"):
    conn = _conn()
    cur = conn.execute("INSERT INTO projects (name) VALUES (?)", (name,))
    pid = cur.lastrowid
    conn.commit()
    conn.close()
    return pid


def delete_project(project_id):
    conn = _conn()
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()


def rename_project(project_id, name):
    conn = _conn()
    conn.execute(
        "UPDATE projects SET name = ?, updated_at = datetime('now') WHERE id = ?",
        (name, project_id),
    )
    conn.commit()
    conn.close()
