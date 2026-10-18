import type { ImageItem, Stats } from './types'

export const API_BASE = 'http://127.0.0.1:8000'
export const WS_URL = 'ws://127.0.0.1:8000/ws'

export function mediaUrl(filename: string): string {
  return `${API_BASE}/media/${filename}`
}

export async function fetchImages(q = ''): Promise<ImageItem[]> {
  const url = new URL(`${API_BASE}/api/images`)
  const query = q.trim()
  if (query) url.searchParams.set('q', query)

  const res = await fetch(url)
  if (!res.ok) throw new Error(`GET /api/images -> ${res.status}`)
  return (await res.json()) as ImageItem[]
}

export async function fetchStats(): Promise<Stats> {
  const res = await fetch(`${API_BASE}/api/stats`)
  if (!res.ok) throw new Error(`GET /api/stats -> ${res.status}`)
  return (await res.json()) as Stats
}

export async function renameImage(id: number, name: string): Promise<ImageItem> {
  const res = await fetch(`${API_BASE}/api/images/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name }),
  })
  if (!res.ok) throw new Error(`PATCH name -> ${res.status}`)
  return (await res.json()) as ImageItem
}

export async function updateTags(id: number, tags: string[]): Promise<ImageItem> {
  const res = await fetch(`${API_BASE}/api/images/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tags }),
  })
  if (!res.ok) throw new Error(`PATCH tags -> ${res.status}`)
  return (await res.json()) as ImageItem
}

export async function deleteImage(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/api/images/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error(`DELETE -> ${res.status}`)
}
