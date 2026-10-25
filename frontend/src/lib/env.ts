function required(name: string, value: string | undefined): string {
  const normalized = value?.trim()
  if (!normalized) {
    throw new Error(`Missing required environment variable: ${name}`)
  }
  return normalized
}

function httpUrl(name: string, value: string | undefined): string {
  const normalized = required(name, value)
  const url = new URL(normalized)
  if (url.protocol !== 'http:' && url.protocol !== 'https:') {
    throw new Error(`${name} must use http or https`)
  }
  return normalized.replace(/\/$/, '')
}

export const env = Object.freeze({
  apiBaseUrl: httpUrl('VITE_API_BASE_URL', import.meta.env.VITE_API_BASE_URL),
  supabaseUrl: httpUrl('VITE_SUPABASE_URL', import.meta.env.VITE_SUPABASE_URL),
  supabaseAnonKey: required(
    'VITE_SUPABASE_ANON_KEY',
    import.meta.env.VITE_SUPABASE_ANON_KEY,
  ),
})
