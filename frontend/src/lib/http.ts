import { env } from '@/lib/env'
import { getAccessToken } from '@/lib/supabase'

const DEFAULT_TIMEOUT_MS = 15_000

export type RequestOptions = Omit<RequestInit, 'body' | 'method'> & {
  timeoutMs?: number
}

export class ApiError extends Error {
  readonly status: number | null
  readonly body: unknown
  readonly isNetworkError: boolean

  constructor(
    message: string,
    options: {
      status: number | null
      body?: unknown
      isNetworkError: boolean
      cause?: unknown
    },
  ) {
    super(message, { cause: options.cause })
    this.name = 'ApiError'
    this.status = options.status
    this.body = options.body
    this.isNetworkError = options.isNetworkError
  }
}

export async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  options: RequestOptions = {},
): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, headers: customHeaders, ...init } =
    options
  const headers = new Headers(customHeaders)
  headers.set('Accept', 'application/json')

  if (body !== undefined) {
    headers.set('Content-Type', 'application/json')
  }

  const accessToken = await getAccessToken()
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`)
  }

  const timeoutSignal = AbortSignal.timeout(timeoutMs)
  const signal = init.signal
    ? AbortSignal.any([init.signal, timeoutSignal])
    : timeoutSignal

  let response: Response
  try {
    response = await fetch(`${env.apiBaseUrl}/${path.replace(/^\//, '')}`, {
      ...init,
      method,
      headers,
      signal,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch (error) {
    const timedOut = error instanceof DOMException && error.name === 'TimeoutError'
    throw new ApiError(timedOut ? 'Request timed out' : 'Network request failed', {
      status: null,
      isNetworkError: true,
      cause: error,
    })
  }

  const responseBody = await parseResponseBody(response)
  if (!response.ok) {
    throw new ApiError(errorMessage(response, responseBody), {
      status: response.status,
      body: responseBody,
      isNetworkError: false,
    })
  }

  return responseBody as T
}

async function parseResponseBody(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return undefined
  }

  const text = await response.text()
  if (!text) {
    return undefined
  }

  return response.headers.get('content-type')?.includes('application/json')
    ? JSON.parse(text)
    : text
}

function errorMessage(response: Response, body: unknown): string {
  if (
    typeof body === 'object' &&
    body !== null &&
    'detail' in body &&
    typeof body.detail === 'string'
  ) {
    return body.detail
  }
  return response.statusText || `Request failed with status ${response.status}`
}
