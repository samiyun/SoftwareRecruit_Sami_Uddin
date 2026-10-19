import { useEffect, useRef, useState } from 'react'
import type { ImageItem, Stats } from './types'
import {
  WS_URL,
  fetchImages,
  fetchStats,
  fetchTags,
  renameImage,
  updateTags,
  deleteImage,
  mediaUrl,
} from './api'

export default function App() {
  const [images, setImages] = useState<ImageItem[]>([])
  const [stats, setStats] = useState<Stats>({ unlabeled: 0, total: 0 })
  const [tagOptions, setTagOptions] = useState<string[]>([])
  const [search, setSearch] = useState('')
  const [wsState, setWsState] = useState<'connecting' | 'open' | 'closed'>(
    'connecting',
  )
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [pendingDelete, setPendingDelete] = useState<ImageItem | null>(null)

  const searchRef = useRef(search)
  searchRef.current = search

  async function loadImages(q: string) {
    try {
      const imgs = await fetchImages(q)
      setImages(imgs)
      setError(null)
    } catch (e) {
      console.error(e)
      setError('Could not reach the backend on port 8000.')
    } finally {
      setLoading(false)
    }
  }

  async function refreshMeta() {
    try {
      const [st, tags] = await Promise.all([fetchStats(), fetchTags()])
      setStats(st)
      setTagOptions(tags)
    } catch {
      /* non-fatal */
    }
  }

  // initial load
  useEffect(() => {
    loadImages('')
    refreshMeta()
  }, [])

  // debounced search
  useEffect(() => {
    const t = setTimeout(() => loadImages(search), 250)
    return () => clearTimeout(t)
  }, [search])

  // live updates over WebSocket
  useEffect(() => {
    let ws: WebSocket | null = null
    let stopped = false
    let retry: ReturnType<typeof setTimeout> | undefined

    function connect() {
      ws = new WebSocket(WS_URL)
      setWsState('connecting')
      ws.onopen = () => setWsState('open')
      ws.onclose = () => {
        setWsState('closed')
        if (!stopped) retry = setTimeout(connect, 2000)
      }
      ws.onerror = () => ws?.close()
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'new_image' && msg.image) {
            const image = msg.image as ImageItem
            if (!searchRef.current.trim()) {
              setImages((prev) => [image, ...prev.filter((i) => i.id !== image.id)])
            } else {
              // keep an active search filtered
              loadImages(searchRef.current)
            }
            refreshMeta()
          }
        } catch {
          /* ignore non-JSON frames */
        }
      }
    }

    connect()
    return () => {
      stopped = true
      if (retry) clearTimeout(retry)
      ws?.close()
    }
  }, [])

  async function handleRename(item: ImageItem, name: string) {
    try {
      const updated = await renameImage(item.id, name)
      setImages((prev) => prev.map((i) => (i.id === updated.id ? updated : i)))
    } catch (e) {
      console.error(e)
      setError('Rename failed.')
    }
  }

  async function handleSetTags(item: ImageItem, tags: string[]) {
    try {
      const updated = await updateTags(item.id, tags)
      setImages((prev) => prev.map((i) => (i.id === updated.id ? updated : i)))
      refreshMeta()
    } catch (e) {
      console.error(e)
      setError('Tag update failed.')
    }
  }

  async function confirmDelete() {
    if (!pendingDelete) return
    const item = pendingDelete
    setPendingDelete(null)
    try {
      await deleteImage(item.id)
      setImages((prev) => prev.filter((i) => i.id !== item.id))
      refreshMeta()
    } catch (e) {
      console.error(e)
      setError('Delete failed.')
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <h1>
          TMR <span className="sep">·</span> Image Database
        </h1>
        <span className={`pill ${wsState}`}>
          {wsState === 'open' ? 'live' : wsState}
        </span>
        <span className="count" title="Images still tagged unlabeled">
          <strong>{stats.unlabeled}</strong> unlabeled
        </span>
        <input
          className="search"
          type="search"
          placeholder="Search by name or tag…"
          aria-label="Search images by name or tag"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </header>

      {error && (
        <div className="toast" role="alert">
          <span>{error}</span>
          <button
            className="toast-x"
            aria-label="Dismiss error"
            onClick={() => setError(null)}
          >
            ×
          </button>
        </div>
      )}

      <main className="grid">
        {loading && images.length === 0 ? (
          <p className="empty">Loading…</p>
        ) : images.length === 0 ? (
          <p className="empty">
            {search
              ? 'No images match your search.'
              : 'No images yet. Start the sender: python sender.py'}
          </p>
        ) : (
          images.map((item) => (
            <ImageCard
              key={item.id}
              item={item}
              onRename={(name) => handleRename(item, name)}
              onSetTags={(tags) => handleSetTags(item, tags)}
              onDelete={() => setPendingDelete(item)}
            />
          ))
        )}
      </main>

      <datalist id="tag-options">
        {tagOptions.map((tag) => (
          <option key={tag} value={tag} />
        ))}
      </datalist>

      {pendingDelete && (
        <div
          className="modal-backdrop"
          onClick={() => setPendingDelete(null)}
          role="presentation"
        >
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="del-title"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 id="del-title">Delete this image?</h2>
            <p className="modal-name">“{pendingDelete.name}”</p>
            <p className="modal-hint">This permanently removes it from the database.</p>
            <div className="modal-actions">
              <button className="btn" onClick={() => setPendingDelete(null)}>
                Cancel
              </button>
              <button className="btn danger" onClick={confirmDelete}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

interface CardProps {
  item: ImageItem
  onRename: (name: string) => void
  onSetTags: (tags: string[]) => void
  onDelete: () => void
}

function ImageCard({ item, onRename, onSetTags, onDelete }: CardProps) {
  const [editingName, setEditingName] = useState(false)
  const [nameDraft, setNameDraft] = useState(item.name)
  const [tagDraft, setTagDraft] = useState('')

  function commitName() {
    const name = nameDraft.trim()
    if (name && name !== item.name) onRename(name)
    setEditingName(false)
  }

  function addTag() {
    const tag = tagDraft.trim()
    if (tag && !item.tags.includes(tag)) onSetTags([...item.tags, tag])
    setTagDraft('')
  }

  return (
    <article className="card">
      <img
        className="thumb"
        src={mediaUrl(item.filename)}
        alt={item.name}
        loading="lazy"
      />

      <div className="meta">
        {editingName ? (
          <input
            className="name-input"
            autoFocus
            value={nameDraft}
            onChange={(e) => setNameDraft(e.target.value)}
            onBlur={commitName}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commitName()
              if (e.key === 'Escape') {
                setNameDraft(item.name)
                setEditingName(false)
              }
            }}
          />
        ) : (
          <button
            className="name"
            title="Click to rename"
            onClick={() => {
              setNameDraft(item.name)
              setEditingName(true)
            }}
          >
            {item.name}
          </button>
        )}

        <div className="tags">
          {item.tags.map((tag) => (
            <span
              key={tag}
              className={tag === 'unlabeled' ? 'tag unlabeled' : 'tag'}
            >
              {tag}
              <button
                className="x"
                title="Remove tag"
                aria-label={`Remove tag ${tag}`}
                onClick={() => onSetTags(item.tags.filter((t) => t !== tag))}
              >
                ×
              </button>
            </span>
          ))}
        </div>

        <div className="row">
          <input
            className="tag-input"
            list="tag-options"
            placeholder="add tag…"
            aria-label="Add a tag"
            value={tagDraft}
            onChange={(e) => setTagDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') addTag()
            }}
          />
          <button className="delete" onClick={onDelete} title="Delete image">
            Delete
          </button>
        </div>
      </div>
    </article>
  )
}
