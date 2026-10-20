# TMR Software Recruitment — Submission

This folder contains the **mandatory socket task** and the **Web team task**
(UI Development) for the TMR Fall 2026 software recruitment package.

## Layout

```
SoftwareRecruit_Sami_Uddin/
├── Socket/                    # Mandatory task — socket communication
│   ├── rover.py               # reads Utah.bmp, sends over TCP
│   ├── basestation.py         # receives on :5555, writes output.bmp
│   ├── Utah.bmp               # input image
│   └── notes.md               # research notes (TCP vs UDP, etc.)
├── UI/                        # Web team task — image database app
│   ├── README.md              # full documentation for the web task
│   ├── backend/               # FastAPI + SQLite + WebSocket sender
│   └── frontend/              # React + TypeScript (Vite)
└── README.md
```

---

## 1. Mandatory task — Socket communication

Two scripts, only the Python `socket` module and built-in file I/O.

Run both **from inside `Socket/`** (that is where `Utah.bmp` lives):

```bash
cd Socket

# Terminal 1 — start the base station first (it waits on 127.0.0.1:5555)
python basestation.py

# Terminal 2 — send the image
python rover.py
```

Result: `Socket/output.bmp` — a valid 24-bit bitmap, byte-identical to `Utah.bmp`.

---

## 2. Web team task — UI Development

An image database web app: a Python script streams random images over
**WebSocket**, the browser labels/renames/searches/deletes them, and everything
is persisted in **SQLite**.

Full documentation (architecture, API, decisions, testing): [`UI/README.md`](UI/README.md).

### Quick start (single server, no Node needed)

A prebuilt frontend is included in `UI/frontend/dist/`.

Run it manually:

```bash
cd UI/backend
pip install -r requirements.txt
python -m uvicorn main:app --port 8000
```

Open <http://127.0.0.1:8000/app/>, then in another terminal send images:

```bash
cd UI/backend
python sender.py          # random image every 2s from data/samples/
```

### Frontend development

```bash
cd UI/frontend
npm install
npm run dev               # http://localhost:5173
```

---

## Notes

- `UI/frontend/dist/` is a prebuilt bundle, so the web app runs with only Python.
- `node_modules/` is intentionally **not** included; run `npm install` only if you
  want the Vite dev server.
- Placeholder sample images live in `UI/backend/data/samples/` — replace them with
  a real dataset (e.g. from Kaggle) or point the sender at another folder.
