"""
main.py — backend for the TMR "UI Development" web task.

What it does
------------
A single FastAPI app that:
  * accepts images pushed by the Python sender over a WebSocket (``/ws``),
  * stores each image on disk and records it in SQLite (tagged ``unlabeled``),
  * broadcasts each new image to every connected browser over the same WebSocket,
  * exposes a REST API for list/search, rename, tag, delete and stats,
  * serves the stored image files under ``/media``.

Only the image *transport* from the Python script must be a WebSocket (per the
task). The CRUD operations use plain REST, which is simpler to reason about.

Run
---
    pip install -r requirements.txt
    python -m uvicorn main:app --reload --port 8000

If you have built the frontend (``cd ../frontend && npm run build``), it is also
served at http://127.0.0.1:8000/app/ .
"""

from __future__ import annotations

import json
import logging
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
# Logging / paths
# --------------------------------------------------------------------------- #
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(name)s: %(message)s",
)
logger = logging.getLogger("tmr.ui")

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
IMAGES_DIR = DATA_DIR / "images"
DB_PATH = BASE_DIR / "images.db"
FRONTEND_DIST = BASE_DIR.parent / "frontend" / "dist"

IMAGES_DIR.mkdir(parents=True, exist_ok=True)

UNLABELED = "unlabeled"


# --------------------------------------------------------------------------- #
# Database
# --------------------------------------------------------------------------- #
@contextmanager
def db_conn() -> Iterator[sqlite3.Connection]:
    """Open a short-lived SQLite connection, commit on success, always close."""
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


def tags_from_str(raw: Optional[str]) -> list[str]:
    return [t for t in (raw or "").split(",") if t]


def tags_to_str(tags: list[str]) -> str:
    clean = [t.strip() for t in tags if t.strip()]
    return ",".join(clean) if clean else UNLABELED


def row_to_item(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "name": row["name"],
        "tags": tags_from_str(row["tags"]),
        "filename": row["filename"],
        "created_at": row["created_at"],
    }


# --------------------------------------------------------------------------- #
# Image type sniffing (no third-party image libraries needed)
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
# App
# --------------------------------------------------------------------------- #
app = FastAPI(title="TMR UI backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

init_db()


class ImagePatch(BaseModel):
    """Partial update for an image: either field may be omitted."""

    name: Optional[str] = None
    tags: Optional[list[str]] = None


# --------------------------------------------------------------------------- #
# WebSocket fan-out: sender -> backend -> all browsers
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
            except Exception:  # noqa: BLE001 - client went away
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@app.get("/")
def root() -> dict:
    return {"ok": True, "service": "TMR UI backend", "docs": "/docs"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """
    Clients of two kinds connect here:

    * the Python sender  -> sends raw image bytes (binary frames)
    * browser clients     -> send nothing; receive JSON ``new_image`` events
    """
    await manager.connect(websocket)
    logger.info("ws client connected (%d open)", len(manager.connections))
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
                logger.warning("ignored %d bytes: unrecognised image format", len(data))
                continue

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

            item = row_to_item(row)
            logger.info("stored image #%s (%s, %d bytes)", item["id"], ext, len(data))
            await manager.broadcast({"type": "new_image", "image": item})
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 - never let one client crash the app
        logger.exception("ws client error")
    finally:
        manager.disconnect(websocket)
        logger.info("ws client disconnected (%d open)", len(manager.connections))


# --------------------------------------------------------------------------- #
# REST: read
# --------------------------------------------------------------------------- #
@app.get("/api/images")
def list_images(q: str = "") -> list[dict]:
    """List images newest-first, optionally filtered by name or tag substring."""
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


@app.get("/api/tags")
def list_tags() -> list[str]:
    """Every distinct tag currently in use (used for frontend suggestions)."""
    with db_conn() as db:
        rows = db.execute("SELECT tags FROM images").fetchall()
    seen: set[str] = set()
    for row in rows:
        seen.update(tags_from_str(row["tags"]))
    return sorted(seen)


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
    """Rename an image and/or replace its tag list."""
    with db_conn() as db:
        row = db.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="image not found")

        name = row["name"] if patch.name is None else patch.name.strip()
        if not name:
            raise HTTPException(status_code=400, detail="name cannot be empty")

        tags = row["tags"] if patch.tags is None else tags_to_str(patch.tags)

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
    logger.info("deleted image #%s", image_id)
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Static files
# --------------------------------------------------------------------------- #
app.mount("/media", StaticFiles(directory=str(IMAGES_DIR)), name="media")

# Optional: serve a production build of the frontend from the same server.
if FRONTEND_DIST.is_dir():
    app.mount(
        "/app",
        StaticFiles(directory=str(FRONTEND_DIST), html=True),
        name="frontend",
    )
    logger.info("serving built frontend at /app")
