'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { clearStoredAuth, readStoredAuth } from '@/lib/session';

export default function WorkspaceSettingsPage() {
  const router = useRouter();
  const auth = readStoredAuth();

  function signOut() {
    clearStoredAuth();
    router.push('/auth/login');
  }

  return (
    <main className="min-h-screen bg-[linear-gradient(135deg,_rgba(255,246,214,0.95)_0%,_rgba(244,244,244,1)_45%,_rgba(217,246,238,0.9)_100%)] p-4 lg:p-6">
      <section className="mx-auto w-full max-w-4xl rounded-[24px] border-4 border-black bg-white p-6 shadow-brutal lg:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b-4 border-black pb-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.22em]">Workspace settings</p>
            <h1 className="mt-2 text-3xl font-black uppercase tracking-[-0.03em]">Profile and account</h1>
            <p className="mt-2 text-sm font-medium text-gray-700">Manage the currently signed-in account for this workspace.</p>
          </div>
          <Link className="rounded-[14px] border-4 border-black bg-sun px-4 py-3 text-sm font-black uppercase shadow-brutal" href="/workspace">
            Back to workspace
          </Link>
        </div>

        <div className="mt-6 grid gap-4 lg:grid-cols-2">
          <article className="rounded-[18px] border-4 border-black bg-sky p-4 shadow-brutal">
            <p className="text-xs font-black uppercase tracking-[0.2em]">Profile</p>
            <h2 className="mt-2 text-2xl font-black">{auth?.user.name ?? 'Signed in user'}</h2>
            <p className="mt-2 text-sm font-medium text-gray-800">Email: {auth?.user.email ?? 'unknown'}</p>
            <p className="mt-2 text-sm font-medium text-gray-800">Session token stored locally for the workspace shell.</p>
          </article>

          <article id="billing" className="rounded-[18px] border-4 border-black bg-paper p-4 shadow-brutal">
            <p className="text-xs font-black uppercase tracking-[0.2em]">Billing</p>
            <h2 className="mt-2 text-2xl font-black">Demo-ready workspace</h2>
            <p className="mt-2 text-sm font-medium text-gray-800">
              Billing hooks are reserved here for a production Supabase or Stripe plan, but the current workspace stays fully usable without any payment step.
            </p>
          </article>
        </div>

        <div className="mt-6 flex flex-wrap gap-3">
          <button className="rounded-[14px] border-4 border-black bg-coral px-4 py-3 text-sm font-black uppercase shadow-brutal" onClick={signOut} type="button">
            Sign out
          </button>
          <Link className="rounded-[14px] border-4 border-black bg-white px-4 py-3 text-sm font-black uppercase shadow-brutal" href="/workspace">
            Return to chat
          </Link>
        </div>
      </section>
    </main>
  );
}
