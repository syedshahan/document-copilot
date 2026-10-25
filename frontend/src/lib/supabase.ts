import { createClient } from '@supabase/supabase-js'

import { env } from '@/lib/env'

export const supabase = createClient(env.supabaseUrl, env.supabaseAnonKey)

export async function getAccessToken(): Promise<string | null> {
  const {
    data: { session },
    error,
  } = await supabase.auth.getSession()

  if (error) {
    throw error
  }
  return session?.access_token ?? null
}
