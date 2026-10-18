import { useEffect, useState } from 'react'
import type { ImageItem, Stats } from './types'
import {
  WS_URL,
  fetchImages,
  fetchStats,
  renameImage,
  updateTags,
  deleteImage,
  mediaUrl,
} from './api'

export default function App() {
  const [images, setImages] = useState<ImageItem[]>([])
  const [stats, setStats] = useState<Stats>({ unlabeled: 0, total: 0 })
  const [search, setSearch] = useState('')
  const [wsState, setWsState] = useState<'connecting' | 'open' | 'closed'>(
    'connecting',
  )
  const [error, setError] = useState<string | null>(null)

  async function loadAll(q: string) {
    try {
      const [imgs, st] = await Promise.all([fetchImages(q), fetchStats()])
      setImages(imgs)
      setStats(st)
      setError(null)
    } catch (e) {
      console.error(e)
      setError('Backend not reachable — is it running on port 8000?')
    }
  }

  // initial load
  useEffect(() => {
    loadAll('')
  }, [])

  // debounced search
  useEffect(() => {
    const t = setTimeout(() => loadAll(search), 250)
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
            setImages((prev) => [image, ...prev.filter((i) => i.id !== image.id)])
            fetchStats().then(setStats).catch(() => {})
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
      setError('Rename failed')
    }
  }

  async function handleSetTags(item: ImageItem, tags: string[]) {
    try {
      const updated = await updateTags(item.id, tags)
      setImages((prev) => prev.map((i) => (i.id === updated.id ? updated : i)))
      fetchStats().then(setStats).catch(() => {})
    } catch (e) {
      console.error(e)
      setError('Tag update failed')
    }
  }

  async function handleDelete(item: ImageItem) {
    if (!window.confirm(`Delete "${item.name}"?`)) return
    try {
      await deleteImage(item.id)
      setImages((prev) => prev.filter((i) => i.id !== item.id))
      fetchStats().then(setStats).catch(() => {})
    } catch (e) {
      console.error(e)
      setError('Delete failed')
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <h1>TMR · Image Database</h1>
        <span className={`pill ${wsState}`}>
          {wsState === 'open' ? 'live' : wsState}
        </span>
        <span className="unlabeled" title="Images still tagged unlabeled">
          {stats.unlabeled} unlabeled
        </span>
        <input
          className="search"
          type="search"
          placeholder="Search by name or tag…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </header>

      {error && <div className="error">{error}</div>}

      <main className="grid">
        {images.length === 0 ? (
          <p className="empty">
            No images yet. Start the sender: <code>python sender.py</code>
          </p>
        ) : (
          images.map((item) => (
            <ImageCard
              key={item.id}
              item={item}
              onRename={(name) => handleRename(item, name)}
              onSetTags={(tags) => handleSetTags(item, tags)}
              onDelete={() => handleDelete(item)}
            />
          ))
        )}
      </main>
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
            placeholder="add tag…"
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
