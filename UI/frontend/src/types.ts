export interface ImageItem {
  id: number
  name: string
  tags: string[]
  filename: string
  created_at: string
}

export interface Stats {
  unlabeled: number
  total: number
}
