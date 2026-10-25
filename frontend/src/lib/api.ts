import { request, type RequestOptions } from '@/lib/http'

export type ChatThread = {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export type StoredChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  message_data: unknown
  position: number
  created_at: string
}

export type DocumentLocation = {
  id: string
  ticker: string
  company_name: string
  filing_type: string
  filing_date: string
  fiscal_year: number
  accession_number: string
  source_url: string
  content: string
  chunk_id: string
  chunk_content: string
  page: number | null
  section: string | null
  highlight_start: number | null
  highlight_end: number | null
}

export const api = {
  get<T>(path: string, options?: RequestOptions): Promise<T> {
    return request<T>('GET', path, undefined, options)
  },

  post<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>('POST', path, body, options)
  },

  put<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>('PUT', path, body, options)
  },

  patch<T>(path: string, body?: unknown, options?: RequestOptions): Promise<T> {
    return request<T>('PATCH', path, body, options)
  },

  delete<T>(path: string, options?: RequestOptions): Promise<T> {
    return request<T>('DELETE', path, undefined, options)
  },
}

export const chats = {
  listThreads(options?: RequestOptions) {
    return api.get<ChatThread[]>('/chat/threads', options)
  },

  createThread(title = 'New conversation') {
    return api.post<ChatThread>('/chat/threads', { title })
  },

  listMessages(threadId: string, options?: RequestOptions) {
    return api.get<StoredChatMessage[]>(
      `/chat/threads/${threadId}/messages`,
      options,
    )
  },
}

export const documents = {
  getLocation(documentId: string, chunkId: string, options?: RequestOptions) {
    return api.get<DocumentLocation>(
      `/documents/${documentId}/location/${chunkId}`,
      options,
    )
  },
}

export { ApiError } from '@/lib/http'
