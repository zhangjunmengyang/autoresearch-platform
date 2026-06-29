export type ApiEnvelope<T> = {
  data: T
  warnings: string[]
}

export type RecordItem = {
  id: string
  title?: string
  status?: string
  created_at?: string
  updated_at?: string
  [key: string]: unknown
}

export type ListResponse<T> = {
  items: T[]
  total: number
  limit: number
  offset: number
  sort: string
}

const API_BASE = import.meta.env.VITE_API_URL || ''

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
    ...options,
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `请求失败：${response.status}`)
  }
  return response.json() as Promise<T>
}

export async function requestEnvelope<T>(path: string, options: RequestInit = {}): Promise<ApiEnvelope<T>> {
  return request<ApiEnvelope<T>>(path, options)
}

export async function getData<T>(path: string): Promise<T> {
  const envelope = await request<ApiEnvelope<T>>(path)
  return envelope.data
}

export async function getListData<T>(path: string): Promise<ListResponse<T>> {
  return getData<ListResponse<T>>(path)
}

export async function postData<T>(path: string, body: unknown): Promise<T> {
  const envelope = await request<ApiEnvelope<T>>(path, {
    method: 'POST',
    body: JSON.stringify(body),
  })
  return envelope.data
}

export async function patchData<T>(path: string, body: unknown): Promise<T> {
  const envelope = await request<ApiEnvelope<T>>(path, {
    method: 'PATCH',
    body: JSON.stringify(body),
  })
  return envelope.data
}
