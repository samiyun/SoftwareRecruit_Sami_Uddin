"""
main.py — TMR image-database backend.

Responsibilities
----------------
* /ws               WebSocket endpoint. The Python sender pushes raw image bytes
                    here; the backend saves the image, inserts a DB row tagged
                    "unlabeled", and broadcasts the new entry to every connected
                    browser client.
* /api/images       List / search images (by name or tag).
* /api/images/{id}  Rename an image and/or replace its tag list (PATCH).
* /api/images/{id}  Delete an image row + its file (DELETE).
* /api/stats        Unlabeled / total counts.
* /media/{file}     Serves the stored image files.

Run:
    pip install -r requirements.txt
    python -m uvicorn main:app --reload --port 8000
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# --------------------------------------------------------------------------- #
# Paths / config
# --------------------------------------------------------------------------- #
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
DB_PATH = BASE_DIR / "images.db"

IMAGES_DIR.mkdir(parents=True, exist_ok=True)

UNLABELED = "unlabeled"

# --------------------------------------------------------------------------- #
# Database
# --------------------------------------------------------------------------- #
@contextmanager
def db_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db_conn() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS images (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                tags       TEXT NOT NULL DEFAULT 'unlabeled',
                filename   TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def row_to_item(row: sqlite3.Row) -> dict:
    tags = [t for t in (row["tags"] or "").split(",") if t]
    return {
        "id": row["id"],
        "name": row["name"],
        "tags": tags,
        "filename": row["filename"],
        "created_at": row["created_at"],
    }


# --------------------------------------------------------------------------- #
# Image type sniffing (works with zero external image libraries)
# --------------------------------------------------------------------------- #
def detect_ext(data: bytes) -> Optional[str]:
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "gif"
    if data.startswith(b"BM"):
        return "bmp"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


# --------------------------------------------------------------------------- #
# App setup
# --------------------------------------------------------------------------- #
app = FastAPI(title="TMR UI backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


class ImagePatch(BaseModel):
    name: Optional[str] = None
    tags: Optional[list[str]] = None


# --------------------------------------------------------------------------- #
# WebSocket fan-out (sender -> backend -> all browser clients)
# --------------------------------------------------------------------------- #
class ConnectionManager:
    def __init__(self) -> None:
        self.connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, message: dict) -> None:
        text = json.dumps(message)
        dead: list[WebSocket] = []
        for ws in list(self.connections):
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@app.get("/")
def root() -> dict:
    return {"ok": True, "service": "TMR UI backend"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Two kinds of clients connect here:
      * the Python sender -> sends raw image bytes
      * browser clients    -> receive JSON events and never send anything
    """
    await manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break

            data: Optional[bytes] = message.get("bytes")
            if not data:
                continue

            ext = detect_ext(data)
            if ext is None:
                continue  # not a recognised image; ignore

            filename = f"{uuid.uuid4().hex}.{ext}"
            (IMAGES_DIR / filename).write_bytes(data)

            with db_conn() as db:
                cur = db.execute(
                    "INSERT INTO images (name, tags, filename, created_at) "
                    "VALUES (?, ?, ?, ?)",
                    (f"image_{filename[:8]}", UNLABELED, filename, now_iso()),
                )
                row = db.execute(
                    "SELECT * FROM images WHERE id = ?", (cur.lastrowid,)
                ).fetchone()

            await manager.broadcast({"type": "new_image", "image": row_to_item(row)})
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


# --------------------------------------------------------------------------- #
# REST: read
# --------------------------------------------------------------------------- #
@app.get("/api/images")
def list_images(q: str = "") -> list[dict]:
    query = q.strip()
    with db_conn() as db:
        if query:
            like = f"%{query}%"
            rows = db.execute(
                "SELECT * FROM images WHERE name LIKE ? OR tags LIKE ? "
                "ORDER BY id DESC",
                (like, like),
            ).fetchall()
        else:
            rows = db.execute("SELECT * FROM images ORDER BY id DESC").fetchall()
    return [row_to_item(r) for r in rows]


@app.get("/api/images/{image_id}")
def get_image(image_id: int) -> dict:
    with db_conn() as db:
        row = db.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="image not found")
    return row_to_item(row)


@app.get("/api/stats")
def stats() -> dict:
    with db_conn() as db:
        total = db.execute("SELECT COUNT(*) AS c FROM images").fetchone()["c"]
        unlabeled = db.execute(
            "SELECT COUNT(*) AS c FROM images "
            "WHERE (',' || tags || ',') LIKE '%,unlabeled,%'"
        ).fetchone()["c"]
    return {"unlabeled": unlabeled, "total": total}


# --------------------------------------------------------------------------- #
# REST: write
# --------------------------------------------------------------------------- #
@app.patch("/api/images/{image_id}")
def patch_image(image_id: int, patch: ImagePatch) -> dict:
    with db_conn() as db:
        row = db.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="image not found")

        name = row["name"] if patch.name is None else patch.name.strip()
        if patch.tags is None:
            tags = row["tags"]
        else:
            clean = [t.strip() for t in patch.tags if t.strip()]
            tags = ",".join(clean) if clean else UNLABELED

        db.execute(
            "UPDATE images SET name = ?, tags = ? WHERE id = ?",
            (name, tags, image_id),
        )
        row = db.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()

    return row_to_item(row)


@app.delete("/api/images/{image_id}")
def delete_image(image_id: int) -> dict:
    with db_conn() as db:
        row = db.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="image not found")
        db.execute("DELETE FROM images WHERE id = ?", (image_id,))

    path = IMAGES_DIR / row["filename"]
    if path.exists():
        path.unlink()
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Static image files
# --------------------------------------------------------------------------- #
app.mount("/media", StaticFiles(directory=str(IMAGES_DIR)), name="media")
