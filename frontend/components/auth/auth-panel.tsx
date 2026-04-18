'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useMemo, useState } from 'react';

import { getApiBaseUrl } from '@/lib/api';
import { writeStoredAuth } from '@/lib/session';

type AuthMode = 'login' | 'signup';

type AuthPanelProps = {
  mode: AuthMode;
};

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(payload?.detail ?? payload?.error ?? 'Request failed');
  }
  return payload as T;
}

export function AuthPanel({ mode }: AuthPanelProps) {
  const router = useRouter();
  const isLogin = mode === 'login';
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const title = useMemo(() => (isLogin ? 'Sign in to the workspace' : 'Create your workspace'), [isLogin]);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setError('');

    try {
      if (isLogin) {
        const payload = await fetchJson<{
          data: {
            user: { id: string; name: string; email: string; created_at?: string };
            session: { token: string; mode: 'authenticated'; user_id?: string };
            default_chat_ids: string[];
          };
        }>(`${getApiBaseUrl()}/auth/login`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });

        writeStoredAuth({ session: payload.data.session, user: payload.data.user });
        router.push(payload.data.default_chat_ids[0] ? `/workspace/${payload.data.default_chat_ids[0]}` : '/workspace');
        return;
      }

      const payload = await fetchJson<{
        data: {
          user: { id: string; name: string; email: string; created_at?: string };
          session: { token: string; mode: 'authenticated'; user_id?: string };
          bootstrap_chat_id?: string;
        };
      }>(`${getApiBaseUrl()}/auth/signup`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password, confirm_password: confirmPassword })
      });

      writeStoredAuth({ session: payload.data.session, user: payload.data.user });
      router.push(payload.data.bootstrap_chat_id ? `/workspace/${payload.data.bootstrap_chat_id}` : '/workspace');
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Unable to authenticate right now.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[radial-gradient(circle_at_top,_rgba(255,224,138,0.9),_rgba(245,245,245,1)_52%,_rgba(184,230,219,0.85)_100%)] px-6 py-16">
      <section className="w-full max-w-2xl rounded-[28px] border-4 border-black bg-white p-8 shadow-brutal md:p-10">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="inline-flex -rotate-2 rounded-[14px] border-4 border-black bg-sky px-4 py-2 text-xs font-black uppercase tracking-[0.3em] shadow-brutal">
            {isLogin ? 'Welcome back' : 'New workspace'}
          </div>
          <div className="rounded-[14px] border-4 border-black bg-paper px-4 py-2 text-xs font-black uppercase tracking-[0.24em] shadow-brutal">
            Demo stays separate
          </div>
        </div>

        <h1 className="mt-5 text-4xl font-black uppercase tracking-[-0.03em] md:text-5xl">{title}</h1>
        <p className="mt-3 max-w-2xl text-sm font-medium leading-7 md:text-base">
          {isLogin
            ? 'Sign in to reopen older chats, keep document uploads attached to a single workspace, and continue with persistent memory.'
            : 'Create an authenticated workspace that keeps chats, uploaded documents, memory, and retrieval metrics together.'}
        </p>

        <form className="mt-8 space-y-4" onSubmit={onSubmit}>
          {!isLogin ? (
            <input
              className="w-full rounded-[18px] border-4 border-black bg-paper px-4 py-3 font-medium outline-none"
              placeholder="Name"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
          ) : null}
          <input
            className="w-full rounded-[18px] border-4 border-black bg-paper px-4 py-3 font-medium outline-none"
            placeholder="Email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
          <input
            className="w-full rounded-[18px] border-4 border-black bg-paper px-4 py-3 font-medium outline-none"
            placeholder="Password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {!isLogin ? (
            <input
              className="w-full rounded-[18px] border-4 border-black bg-paper px-4 py-3 font-medium outline-none"
              placeholder="Confirm password"
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
            />
          ) : null}
          {error ? (
            <div className="rounded-[16px] border-4 border-black bg-coral px-4 py-3 text-sm font-bold shadow-brutal">{error}</div>
          ) : null}
          <button
            className="w-full rounded-[18px] border-4 border-black bg-coral px-4 py-4 text-lg font-black uppercase tracking-[0.08em] shadow-brutal transition-transform hover:-translate-x-1 hover:-translate-y-1 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={isSubmitting}
            type="submit"
          >
            {isSubmitting ? 'Working...' : isLogin ? 'Login' : 'Sign up'}
          </button>
        </form>

        <div className="my-8 flex items-center gap-4 text-sm font-black uppercase tracking-[0.2em]">
          <span className="h-px flex-1 bg-black" />
          <span>Or</span>
          <span className="h-px flex-1 bg-black" />
        </div>

        <div className="grid gap-3">
          <Link
            className="inline-flex items-center justify-center rounded-[18px] border-4 border-black bg-sun px-6 py-4 text-lg font-black uppercase tracking-[0.08em] shadow-brutal transition-transform duration-150 hover:-translate-x-1 hover:-translate-y-1"
            href="/demo"
          >
            Skip setup → Enter demo workspace
          </Link>
          <Link className="text-sm font-bold underline decoration-4 underline-offset-4" href={isLogin ? '/auth/signup' : '/auth/login'}>
            {isLogin ? 'Need an account? Sign up' : 'Already have an account? Sign in'}
          </Link>
        </div>
      </section>
    </main>
  );
}
