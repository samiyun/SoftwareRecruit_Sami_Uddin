# UI — Web Team Task (Image Database)

A functional, visually polished web application for receiving images over
**WebSocket**, labelling them into a **database**, and **searching** that
database. Built for the TMR Fall 2026 software recruitment package.

---

## 1. What it does

1. A **Python script** (`backend/sender.py`) picks a random image from a folder
   and pushes it to the app over a **WebSocket** (this is the task's required
   transport for image data).
2. The **backend** saves the image, inserts a row in **SQLite** tagged
   `unlabeled`, and broadcasts the new image to every connected browser.
3. The **browser** shows the image live. The user can:
   - **rename** it (click the name),
   - **label** it with tags (add/remove chips, with autocomplete),
   - **search** the database by name or tag,
   - **delete** entries through a confirmation modal.
4. The header shows a live **count of images still unlabeled**.

---

## 2. How it satisfies the task requirements

| Requirement | Implementation |
|---|---|
| Python script sends a randomly selected image via WebSocket | `backend/sender.py` → `WS /ws` (binary frames) |
| Frontend only JavaScript / TypeScript | React + TypeScript (`frontend/src`) |
| Rename, label and save incoming images to a database | `PATCH /api/images/{id}` + SQLite |
| Search saved images by name or tag | `GET /api/images?q=` (name OR tags) |
| Incoming images tagged `unlabeled` | insert default in `main.py` |
| Indicator of unlabelled count | `GET /api/stats` + header `count` |
| Modify or delete entries graphically | inline rename, tag chips, delete modal |
| Images from Python transmitted only over WebSocket | sender uses `websockets`, never HTTP |

---

## 3. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Backend | Python 3.10+ · **FastAPI** | one process for WS + REST |
| WebSocket | `websockets` (client) / Starlette (server) | binary image frames |
| Database | **SQLite** (`sqlite3`, stdlib) | zero-setup, single file |
| Images | files on disk (`backend/data/images/`) | DB stores the filename |
| Frontend | **React 18 + TypeScript**, bundled with **Vite** | dev server on :5173 |
| Styling | plain CSS (`frontend/src/styles.css`) | no UI framework |

---

## 4. Project structure

```
UI/
├── README.md
├── .gitignore
├── backend/
│   ├── main.py              # FastAPI: WS ingest + REST API + static media
│   ├── sender.py            # the required Python WebSocket sender
│   ├── requirements.txt
│   ├── images.db            # created at runtime (git-ignored)
│   └── data/
│       ├── images/          # received images (git-ignored)
│       └── samples/         # drop a dataset here for the sender
└── frontend/
    ├── package.json
    ├── vite.config.ts
    ├── tsconfig.json
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx          # UI + WebSocket client + REST calls
        ├── api.ts           # typed fetch helpers
        ├── types.ts
        └── styles.css
```

---

## 5. Prerequisites

- **Python 3.10+**
- **Node.js 18+** (for the frontend; npm or pnpm)

---

## 6. Run it

### Terminal 1 — backend

```bash
cd UI/backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

Once running:
- API docs: <http://127.0.0.1:8000/docs>
- Health: <http://127.0.0.1:8000/>

### Terminal 2 — frontend

```bash
cd UI/frontend
npm install        # or: pnpm install
npm run dev
```

Open <http://localhost:5173>.

### Terminal 3 — sender

```bash
cd UI/backend
python sender.py
```

That sends a random image every 2 s from `backend/data/samples/`.

No dataset yet? Point it at any folder of images:

```bash
python sender.py --folder ../Socket     # quick test: sends Utah.bmp
python sender.py --count 5 --delay 0.5  # five images, fast
python sender.py --folder C:/datasets/butterflies
```

---

## 7. Optional: single-server deployment

Build the frontend once and let the backend serve it (no Node needed at run time):

```bash
cd UI/frontend
npm install
npm run build            # produces frontend/dist
```

Restart the backend and open <http://127.0.0.1:8000/app/>.

---

## 8. Using the app

- **Receive** — with the backend + frontend open, run `sender.py`; images appear
  live and are tagged `unlabeled`.
- **Label** — type a tag name in "add tag…" and press Enter. Use the `×` on the
  `unlabeled` chip to mark the image as labelled (the count drops).
- **Rename** — click the image name, type, press Enter (Esc cancels).
- **Search** — type in the search bar; matches name **or** tags, case-insensitive.
- **Delete** — click **Delete**, confirm in the modal; the row and the file are removed.

---

## 9. Architecture

```
 ┌──────────────┐   binary frames    ┌──────────────────────────┐
 │ sender.py    │ ───── WS ────────▶ │ FastAPI  /ws             │
 │ (random img) │                    │  1. save file to disk    │
 └──────────────┘                    │  2. INSERT row (unlabel) │
                                     │  3. broadcast JSON       │
 ┌──────────────┐   JSON events      │                          │
 │ Browser      │ ◀─── WS ────────── │                          │
 │ (React + TS) │                    │  REST /api/*  ── SQLite  │
 │              │ ── fetch (CRUD) ─▶ │                          │
 └──────────────┘                    └──────────────────────────┘
```

Key points:
- `/ws` is shared: the **sender** only writes binary frames; **browsers** only
  read JSON events. One endpoint, two roles.
- Image *transport* from Python is WebSocket-only (task requirement). CRUD is
  REST because it is simpler and easier to reason about.
- The DB stores metadata; images live as files and are served from `/media`.

---

## 10. API reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | health check |
| `WS` | `/ws` | image ingest (sender) + live updates (browser) |
| `GET` | `/api/images?q=` | list newest-first; `q` filters by name or tag |
| `GET` | `/api/images/{id}` | single image |
| `PATCH` | `/api/images/{id}` | `{ "name"?: string, "tags"?: string[] }` |
| `DELETE` | `/api/images/{id}` | delete row + file |
| `GET` | `/api/tags` | distinct tags (autocomplete) |
| `GET` | `/api/stats` | `{ "unlabeled": n, "total": n }` |
| `GET` | `/media/{filename}` | the stored image file |

Interactive docs are auto-generated at `/docs`.

### Example

```bash
curl http://127.0.0.1:8000/api/images
curl "http://127.0.0.1:8000/api/images?q=monarch"
curl -X PATCH http://127.0.0.1:8000/api/images/3 \
     -H "Content-Type: application/json" \
     -d '{"name":"Monarch","tags":["Colour:Orange","Species:Monarch"]}'
curl -X DELETE http://127.0.0.1:8000/api/images/3
```

---

## 11. Data model

`images` table:

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | autoincrement |
| `name` | TEXT | display name; editable |
| `tags` | TEXT | comma-separated tags, e.g. `Colour:Orange,Species:Monarch` |
| `filename` | TEXT | file under `data/images/` |
| `created_at` | TEXT | ISO-8601 UTC timestamp |

Tags are stored comma-separated (simple and greppable). An image with no tags
falls back to the tag `unlabeled`, so every image always has at least one tag.

---

## 12. Design decisions

- **WebSocket for images, REST for CRUD.** The task only constrains how the
  Python script sends image data. Using WS for transport and REST for metadata
  keeps each concern simple.
- **SQLite + files on disk.** No external DB service; the DB stays small and
  images are easy to inspect. (`sqlite3` is in the Python standard library.)
- **Comma-separated tags.** Avoids a join table for a recruitment-scale app and
  makes `LIKE` search trivial. A production version would use a `tags` table.
- **Auto-detect image type by magic bytes.** The sender streams raw bytes; the
  server sniffs JPEG/PNG/GIF/BMP/WEBP and picks the right extension, so the
  browser can render it.
- **Broadcast to all clients.** New images appear live without polling; the
  browser also reconnects automatically if the backend restarts.
- **Open CORS.** Dev convenience (Vite on :5173, API on :8000). Tighten for prod.

---

## 13. Testing checklist

- [ ] `python sender.py --count 1` → an image appears live, tagged `unlabeled`
- [ ] Unlabelled counter increases by 1
- [ ] Add a tag, remove `unlabeled` → counter decreases
- [ ] Rename → persists after refresh (F5)
- [ ] Search by a tag → filters correctly
- [ ] Search by name → filters correctly
- [ ] Delete → confirmation modal → row disappears, counter updates
- [ ] Restart backend → all data still present (SQLite persistence)
- [ ] Stop/restart backend → browser WS reconnects automatically

---

## 14. Known limitations / next steps

- Tags are free-form (no controlled vocabulary or per-category UI).
- No pagination — fine for hundreds of images, not millions.
- No authentication (single local user).
- Live events aren't filtered client-side while a search is active; the list is
  refetched instead.

---

## 15. Troubleshooting

| Symptom | Fix |
|---|---|
| Frontend says "Could not reach the backend" | start the backend on port 8000 |
| Sender prints "No images found" | put images in `data/samples/` or pass `--folder` |
| Sender retries "connection failed" | backend isn't running yet |
| Images don't render | check `/media/<filename>` loads; unsupported format |
| Port already in use | stop the other process or change `--port` |
