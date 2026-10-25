import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { supabase } from '@/lib/supabase'

type AuthPageProps = {
  mode: 'sign-in' | 'sign-up'
}

export function AuthPage({ mode }: AuthPageProps) {
  const navigate = useNavigate()
  const isSignUp = mode === 'sign-up'
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setMessage(null)

    const form = new FormData(event.currentTarget)
    const email = String(form.get('email'))
    const password = String(form.get('password'))

    if (isSignUp && password !== String(form.get('confirmPassword'))) {
      setError('Passwords do not match.')
      return
    }

    setIsSubmitting(true)
    try {
      if (isSignUp) {
        const { data, error: signUpError } = await supabase.auth.signUp({
          email,
          password,
          options: {
            emailRedirectTo: `${window.location.origin}/sign-in`,
          },
        })
        if (signUpError) throw signUpError

        if (data.session) {
          navigate('/workspace', { replace: true })
          return
        }
        setMessage('Check your inbox and confirm your email to finish signing up.')
        event.currentTarget.reset()
      } else {
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email,
          password,
        })
        if (signInError) throw signInError

        navigate('/workspace', { replace: true })
      }
    } catch (submissionError) {
      setError(
        submissionError instanceof Error
          ? submissionError.message
          : 'Authentication failed. Please try again.',
      )
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <main className="flex min-h-svh items-center justify-center bg-muted/40 px-4 py-10">
      <Card className="w-full max-w-md shadow-sm">
        <CardHeader>
          <CardTitle className="text-2xl">
            {isSignUp ? 'Create your account' : 'Welcome back'}
          </CardTitle>
          <CardDescription>
            {isSignUp
              ? 'Use your work email to start using Document Copilot.'
              : 'Sign in to continue to Document Copilot.'}
          </CardDescription>
        </CardHeader>

        <CardContent>
          <form className="space-y-4" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <Label htmlFor={`${mode}-email`}>Email</Label>
              <Input
                id={`${mode}-email`}
                name="email"
                type="email"
                autoComplete="email"
                placeholder="analyst@company.com"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor={`${mode}-password`}>Password</Label>
              <Input
                id={`${mode}-password`}
                name="password"
                type="password"
                autoComplete={isSignUp ? 'new-password' : 'current-password'}
                minLength={8}
                required
              />
              {isSignUp && (
                <p className="text-xs text-muted-foreground">
                  Use at least 8 characters.
                </p>
              )}
            </div>

            {isSignUp && (
              <div className="space-y-2">
                <Label htmlFor="confirm-password">Confirm password</Label>
                <Input
                  id="confirm-password"
                  name="confirmPassword"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  required
                />
              </div>
            )}

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {message && (
              <Alert>
                <AlertDescription>{message}</AlertDescription>
              </Alert>
            )}

            <Button className="w-full" type="submit" disabled={isSubmitting}>
              {isSubmitting
                ? isSignUp
                  ? 'Creating account…'
                  : 'Signing in…'
                : isSignUp
                  ? 'Create account'
                  : 'Sign in'}
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-muted-foreground">
            {isSignUp ? 'Already have an account?' : 'Need an account?'}{' '}
            <Link
              className="font-medium text-foreground underline underline-offset-4"
              to={isSignUp ? '/sign-in' : '/sign-up'}
            >
              {isSignUp ? 'Sign in' : 'Sign up'}
            </Link>
          </p>
        </CardContent>
      </Card>
    </main>
  )
}
