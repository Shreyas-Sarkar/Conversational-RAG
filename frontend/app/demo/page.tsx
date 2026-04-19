import Link from 'next/link';

import { getApiBaseUrl } from '@/lib/api';

async function getDemoPayload() {
  const response = await fetch(`${getApiBaseUrl()}/demo`, { method: 'POST', cache: 'no-store' });
  if (!response.ok) {
    throw new Error('Failed to load demo payload');
  }
  const envelope = await response.json();
  return envelope.data ?? envelope;
}

export default async function DemoPage() {
  const payload = await getDemoPayload();
  const seededChats = payload.seeded_chats ?? [];
  const guidedPrompts = payload.guided_prompts ?? [];

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <section className="rounded-[24px] border-4 border-black bg-sun p-6 shadow-brutal">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-black uppercase tracking-[0.2em]">DEMO ACCOUNT</p>
            <h1 className="mt-2 text-4xl font-black">Pick a seeded workspace</h1>
            <p className="mt-3 max-w-3xl text-lg">
              Each conversation keeps its own documents and answer history isolated inside a seeded workspace.
            </p>
          </div>
          <div className="rounded-[18px] border-4 border-black bg-white px-4 py-3 text-sm font-black shadow-brutal">
            Reset daily
          </div>
        </div>
      </section>

      <section className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        {seededChats.map((chat: { id: string; title: string }) => (
          <article key={chat.id} className="rounded-[18px] border-4 border-black bg-white p-4 shadow-brutal">
            <p className="text-xs font-bold uppercase tracking-[0.2em]">Chat</p>
            <h2 className="mt-2 text-2xl font-black">{chat.title}</h2>
            <p className="mt-2 text-sm font-medium">Open the live chat and retrieve only its seeded knowledge base.</p>
            <div className="mt-4 flex flex-wrap gap-3">
              <Link
                href={`/chat/${chat.id}`}
                className="inline-flex rounded-[14px] border-4 border-black bg-coral px-4 py-2 font-bold shadow-brutal"
              >
                Open chat
              </Link>
              <span className="inline-flex rounded-[14px] border-4 border-black bg-paper px-4 py-2 text-sm font-bold shadow-brutal">
                Seeded
              </span>
            </div>
          </article>
        ))}
      </section>

      <section className="mt-6 rounded-[24px] border-4 border-black bg-paper p-6 shadow-brutal">
        <p className="text-xs font-bold uppercase tracking-[0.2em]">Guided onboarding</p>
        <div className="mt-4 flex flex-wrap gap-3">
          {guidedPrompts.map((prompt: string) => (
            <div key={prompt} className="rounded-full border-4 border-black bg-white px-4 py-2 font-bold shadow-brutal">
              {prompt}
            </div>
          ))}
        </div>
      </section>
    </main>
  );
}
