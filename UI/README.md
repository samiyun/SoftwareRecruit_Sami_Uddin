# UI — TMR Image Database (Web team task)

Web app for receiving images over **WebSocket**, labelling/saving them to a
database, and searching them.

## Stack
- **Backend:** Python + FastAPI (WebSocket + REST), SQLite (`sqlite3`, stdlib)
- **Frontend:** React + TypeScript (Vite)
- **Images:** stored on disk in `backend/data/images/`, metadata in `backend/images.db`

## Run it (3 terminals)

### 1. Backend
```bash
cd UI/backend
pip install -r requirements.txt
python -m uvicorn main:app --reload --port 8000
```

### 2. Frontend
```bash
cd UI/frontend
npm install
npm run dev
```
Open <http://localhost:5173>.

### 3. Sender (the required Python script)
```bash
cd UI/backend
python sender.py                    # random image every 2s from data/samples/
python sender.py --folder ../Socket # quick test: sends Utah.bmp
```

## How it works
1. `sender.py` connects to `ws://127.0.0.1:8000/ws` and sends **raw image bytes**.
2. The backend saves the file, inserts a DB row tagged **`unlabeled`**, and
   broadcasts the new entry over WebSocket to the browser.
3. The browser shows it live. Add a real tag and remove `unlabeled` to mark it labelled.
4. Search filters by **name or tag**; the top-right counter shows unlabelled count.
5. Rename (click the name), add/remove tags, or delete entries.

## API
| Method | Path | Purpose |
|---|---|---|
| GET  | `/api/images?q=` | list / search by name or tag |
| PATCH| `/api/images/{id}` | rename and/or replace tags |
| DELETE | `/api/images/{id}` | delete row + file |
| GET  | `/api/stats` | `{ unlabeled, total }` |
| GET  | `/media/{file}` | serve stored image |
| WS   | `/ws` | image upload (sender) + live updates (browser) |

## Dataset
Drop any `.jpg/.png/.bmp/.gif/.webp` files into `backend/data/samples/`
(or point `--folder` at a Kaggle dataset folder).
