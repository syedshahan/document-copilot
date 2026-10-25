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

export { ApiError } from '@/lib/http'
