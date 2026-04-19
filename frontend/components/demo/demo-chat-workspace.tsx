'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';

import { getApiBaseUrl } from '@/lib/api';

type DemoChatSeed = {
  id: string;
  title: string;
  namespace: string;
};

type ChatMessage = {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: Array<Record<string, unknown>>;
};

type RetrievalSource = {
  chunk_id: string;
  document_id: string;
  filename: string;
  page_number: number;
  chunk_index: number;
  similarity: number;
  chunk_text: string;
};

type QueryResult = {
  chat_id: string;
  answer: string;
  sources: RetrievalSource[];
  retrieval_count: number;
  confidence: number;
  latency_ms: number;
  used_llm: boolean;
  namespace?: string;
  memory_summary?: string;
};

type DemoPayload = {
  seeded_chats?: Array<{ id: string; title: string }>;
  namespace_map?: Record<string, string>;
  guided_prompts?: string[];
};

type DemoEnvelope = {
  data?: DemoPayload;
  seeded_chats?: Array<{ id: string; title: string }>;
  namespace_map?: Record<string, string>;
  guided_prompts?: string[];
};

const ACTIVE_CHAT_KEY = 'demo.activeChat';
const MESSAGE_PREFIX = 'demo.messages.';

const DEFAULT_CHAT_MAP: Record<string, DemoChatSeed> = {
  'oracle-fusion-migration-docs': { id: 'oracle-fusion-migration-docs', title: 'Oracle Fusion Migration Docs', namespace: 'demo_oracle' },
  'compliance-handbook': { id: 'compliance-handbook', title: 'Compliance Handbook', namespace: 'demo_compliance' },
  'research-papers': { id: 'research-papers', title: 'Research Papers', namespace: 'demo_research' },
  'resume-job-description-analysis': { id: 'resume-job-description-analysis', title: 'Resume + JD Analysis', namespace: 'demo_resume' }
};

function readStoredChat(chatId: string): ChatMessage[] | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const raw = window.localStorage.getItem(`${MESSAGE_PREFIX}${chatId}`);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as ChatMessage[];
  } catch {
    return null;
  }
}

function writeStoredChat(chatId: string, messages: ChatMessage[]) {
  window.localStorage.setItem(`${MESSAGE_PREFIX}${chatId}`, JSON.stringify(messages));
}

function readStoredActiveChat(): DemoChatSeed | null {
  if (typeof window === 'undefined') {
    return null;
  }
  const raw = window.localStorage.getItem(ACTIVE_CHAT_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as DemoChatSeed;
  } catch {
    return null;
  }
}

function writeStoredActiveChat(activeChat: DemoChatSeed) {
  window.localStorage.setItem(ACTIVE_CHAT_KEY, JSON.stringify(activeChat));
}

function formatLatency(latencyMs?: number) {
  if (!latencyMs) {
    return '0.0 sec';
  }
  return `${(latencyMs / 1000).toFixed(1)} sec`;
}

function looksLikeStorageName(value: string) {
  return /^(?:[a-f0-9]{16,}|[a-f0-9-]{32,})(?:\.[a-z0-9]+)?$/i.test(value.trim());
}

function humanizeSourceName(value: string) {
  if (looksLikeStorageName(value)) {
    return 'Uploaded document';
  }
  return value.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export function DemoChatWorkspace({ initialChatId }: { initialChatId?: string }) {
  const router = useRouter();
  const [demoPayload, setDemoPayload] = useState<DemoPayload | null>(null);
  const [activeChat, setActiveChat] = useState<DemoChatSeed | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [input, setInput] = useState('Explain Oracle migration');
  const [latestSources, setLatestSources] = useState<RetrievalSource[]>([]);
  const [latestMetrics, setLatestMetrics] = useState<{ namespace?: string; retrieval_count?: number; latency_ms?: number; top_k: number; threshold: number }>({
    top_k: 4,
    threshold: 0.2
  });
  const endRef = useRef<HTMLDivElement | null>(null);

  const selectedChatId = activeChat?.id ?? initialChatId ?? '';

  const chatList = useMemo(() => demoPayload?.seeded_chats ?? [], [demoPayload]);
  const namespaceMap = demoPayload?.namespace_map ?? {};
  const guidedPrompts = demoPayload?.guided_prompts ?? [];

  useEffect(() => {
    const stored = readStoredActiveChat();
    const fallbackId = initialChatId || stored?.id || 'oracle-fusion-migration-docs';
    const fallback = DEFAULT_CHAT_MAP[fallbackId] ?? DEFAULT_CHAT_MAP['oracle-fusion-migration-docs'];
    setActiveChat(stored ?? fallback);

    let cancelled = false;
    (async () => {
      try {
        const envelope = await fetchJson<DemoEnvelope>(`${getApiBaseUrl()}/demo`, { method: 'POST' });
        const payload = envelope.data ?? envelope;
        if (cancelled) return;
        setDemoPayload(payload);

        const seededChats = payload.seeded_chats ?? [];
        const fallbackId = initialChatId || stored?.id || seededChats[0]?.id || fallback.id;
        const selected = seededChats.find((chat) => chat.id === fallbackId) ?? seededChats[0] ?? fallback;
        if (selected) {
          const namespace = payload.namespace_map?.[selected.id] ?? DEFAULT_CHAT_MAP[selected.id]?.namespace ?? '';
          const seededChat = { ...selected, namespace };
          setActiveChat(seededChat);
          writeStoredActiveChat(seededChat);
        }
      } catch {
        // keep the UI usable even if demo bootstrap call fails
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [initialChatId]);

  useEffect(() => {
    if (!activeChat) {
      return;
    }

    let cancelled = false;
    setIsLoadingHistory(true);
    const stored = readStoredChat(activeChat.id);
    if (stored && stored.length > 0) {
      setMessages(stored);
      setIsLoadingHistory(false);
      return;
    }

    (async () => {
      try {
        const payload = await fetchJson<{ data: { messages: ChatMessage[]; memory_summary: string } }>(
          `${getApiBaseUrl()}/chat-history?chat_id=${encodeURIComponent(activeChat.id)}`
        );
        if (cancelled) return;
        setMessages(payload.data.messages || []);
        writeStoredChat(activeChat.id, payload.data.messages || []);
      } catch {
        if (!cancelled) {
          setMessages([]);
        }
      } finally {
        if (!cancelled) {
          setIsLoadingHistory(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [activeChat?.id]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText]);

  function switchChat(chat: DemoChatSeed) {
    const namespace = namespaceMap[chat.id] ?? DEFAULT_CHAT_MAP[chat.id]?.namespace ?? chat.namespace;
    const nextChat = { ...chat, namespace };
    setActiveChat(nextChat);
    writeStoredActiveChat(nextChat);
    router.push(`/chat/${chat.id}`);
  }

  async function submitMessage(nextMessage: string) {
    if (!activeChat || !nextMessage.trim()) return;

    const userMessage: ChatMessage = {
      id: `${activeChat.id}-user-${Date.now()}`,
      role: 'user',
      content: nextMessage.trim(),
      sources: []
    };

    const optimisticMessages = [...messages, userMessage];
    setMessages(optimisticMessages);
    writeStoredChat(activeChat.id, optimisticMessages);
    setInput('');
    setStreamingText('');
    setIsStreaming(true);
    setLatestSources([]);

    const response = await fetch(`${getApiBaseUrl()}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: activeChat.id,
        message: nextMessage.trim(),
        top_k: 4,
        similarity_threshold: 0.2
      })
    });

    if (!response.body) {
      setIsStreaming(false);
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let assistantDraft = '';
    let hasFinalPayload = false;

    const flushAssistantDraft = () => {
      const assistantMessage: ChatMessage = {
        id: `${activeChat.id}-assistant-${Date.now()}`,
        role: 'assistant',
        content: assistantDraft.trim() || 'I could not generate a response.',
        sources: latestSources as Array<Record<string, unknown>>
      };
      const nextMessages = [...optimisticMessages, assistantMessage];
      setMessages(nextMessages);
      writeStoredChat(activeChat.id, nextMessages);
    };

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split('\n\n');
        buffer = events.pop() ?? '';

        for (const event of events) {
          const dataLine = event.split('\n').find((line) => line.startsWith('data: '));
          if (!dataLine) continue;
          const raw = dataLine.slice(6);
          const parsed = JSON.parse(raw) as { type: 'token' | 'final'; value: any };

          if (parsed.type === 'token') {
            assistantDraft = `${assistantDraft}${parsed.value} `;
            setStreamingText(assistantDraft);
          }

          if (parsed.type === 'final') {
            hasFinalPayload = true;
            const finalPayload = parsed.value.data as QueryResult;
            setLatestSources(finalPayload.sources || []);
            setLatestMetrics({
              namespace: finalPayload.namespace,
              retrieval_count: finalPayload.retrieval_count,
              latency_ms: finalPayload.latency_ms,
              top_k: 4,
              threshold: 0.2
            });
            assistantDraft = finalPayload.answer;
            setStreamingText(finalPayload.answer);
            const assistantMessage: ChatMessage = {
              id: `${activeChat.id}-assistant-${Date.now()}`,
              role: 'assistant',
              content: finalPayload.answer,
              sources: finalPayload.sources as Array<Record<string, unknown>>
            };
            const nextMessages = [...optimisticMessages, assistantMessage];
            setMessages(nextMessages);
            writeStoredChat(activeChat.id, nextMessages);
          }
        }
      }
    } finally {
      setIsStreaming(false);
      setStreamingText('');
      if (!hasFinalPayload && assistantDraft) {
        flushAssistantDraft();
      }
    }
  }

  const activeNamespace = activeChat?.namespace ?? namespaceMap[activeChat?.id ?? ''] ?? '';

  return (
    <div className="grid min-h-screen grid-cols-1 gap-4 p-4 lg:grid-cols-[18rem_minmax(0,1fr)_22rem]">
      <aside className="rounded-[18px] border-4 border-black bg-sky p-4 shadow-brutal">
        <div className="inline-flex -rotate-2 rounded-[14px] border-4 border-black bg-sun px-4 py-2 text-xs font-black uppercase tracking-[0.3em] shadow-brutal">
          Demo Chats
        </div>
        <div className="mt-4 space-y-3">
          {chatList.map((chat) => {
            const isActive = chat.id === selectedChatId;
            return (
              <button
                key={chat.id}
                type="button"
                onClick={() => switchChat({ id: chat.id, title: chat.title, namespace: namespaceMap[chat.id] ?? '' })}
                className={`w-full rounded-[18px] border-4 border-black px-4 py-3 text-left shadow-brutal transition-transform hover:-translate-x-1 hover:-translate-y-1 ${
                  isActive ? 'bg-coral' : 'bg-white'
                }`}
              >
                <div className="text-xs font-black uppercase tracking-[0.2em]">{chat.id === selectedChatId ? 'Active' : 'Demo'}</div>
                <div className="mt-1 text-lg font-black leading-6">{chat.title}</div>
                <div className="mt-2 text-xs font-bold opacity-80">Seeded workspace</div>
              </button>
            );
          })}
        </div>
      </aside>

      <main className="rounded-[18px] border-4 border-black bg-white p-4 shadow-brutal">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b-4 border-black pb-4">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.22em]">Active Chat</p>
            <h1 className="mt-2 text-3xl font-black uppercase tracking-[-0.03em]">{activeChat?.title ?? 'Select a demo chat'}</h1>
            <p className="mt-2 text-sm font-medium text-gray-700">Workspace: {activeChat?.title ?? 'loading...'}</p>
          </div>
          <Link href="/demo" className="rounded-[14px] border-4 border-black bg-sun px-4 py-2 font-bold shadow-brutal">
            Back to demo hub
          </Link>
        </div>

        <div className="mt-4 min-h-[55vh] space-y-4 overflow-y-auto pr-2">
          {isLoadingHistory ? (
            <div className="rounded-[18px] border-4 border-black bg-paper p-4 font-black shadow-brutal">Loading chat history...</div>
          ) : null}

          {messages.map((message) => (
            <article
              key={message.id}
              className={`rounded-[18px] border-4 border-black p-4 shadow-brutal ${message.role === 'assistant' ? 'bg-sun' : 'bg-white'}`}
            >
              <div className="text-xs font-black uppercase tracking-[0.2em]">{message.role === 'assistant' ? 'Assistant' : 'User'}</div>
              <p className="mt-2 whitespace-pre-wrap text-base leading-7">{message.content}</p>
              {message.role === 'assistant' && message.sources?.length ? (
                <div className="mt-4 space-y-2">
                  <p className="text-xs font-black uppercase tracking-[0.2em]">Sources</p>
                  {message.sources.map((source) => (
                    <details key={`${String(source.chunk_id)}-${String(source.page_number)}`} className="rounded-[14px] border-2 border-black bg-white p-3">
                      <summary className="cursor-pointer font-bold">
                        {humanizeSourceName(String(source.filename))} · Page {String(source.page_number)} · Similarity {Number(source.similarity).toFixed(2)}
                      </summary>
                      <p className="mt-2 text-sm leading-6 text-gray-800">{String(source.chunk_text)}</p>
                    </details>
                  ))}
                </div>
              ) : null}
            </article>
          ))}

          {isStreaming ? (
            <article className="rounded-[18px] border-4 border-black bg-sun p-4 shadow-brutal">
              <div className="text-xs font-black uppercase tracking-[0.2em]">Assistant is typing...</div>
              <p className="mt-2 whitespace-pre-wrap text-base leading-7">{streamingText || ' '}</p>
            </article>
          ) : null}

          <div ref={endRef} />
        </div>

        <form
          className="sticky bottom-0 mt-4 rounded-[18px] border-4 border-black bg-white p-3 shadow-brutal"
          onSubmit={(event) => {
            event.preventDefault();
            void submitMessage(input);
          }}
        >
          <label className="mb-2 inline-flex -rotate-1 rounded-[12px] border-2 border-black bg-sky px-3 py-1 text-[11px] font-black uppercase tracking-[0.22em] shadow-brutal">
            Ask something
          </label>
          <div className="flex gap-3">
            <input
              className="min-w-0 flex-1 rounded-[14px] border-4 border-black bg-paper px-4 py-3 font-medium outline-none"
              placeholder="Explain Oracle migration..."
              value={input}
              onChange={(event) => setInput(event.target.value)}
            />
            <button
              type="submit"
              className="rounded-[14px] border-4 border-black bg-coral px-5 py-3 font-black uppercase tracking-[0.08em] shadow-brutal transition-transform hover:-translate-x-1 hover:-translate-y-1"
              disabled={isStreaming}
            >
              Send
            </button>
          </div>
        </form>
      </main>

      <aside className="rounded-[18px] border-4 border-black bg-moss p-4 shadow-brutal">
        <div className="inline-flex -rotate-2 rounded-[12px] border-2 border-black bg-sun px-3 py-1 text-[11px] font-black uppercase tracking-[0.22em] shadow-brutal">
          Retrieval Metrics
        </div>
        <div className="mt-4 space-y-3">
          <div className="rounded-[18px] border-4 border-black bg-paper p-3 shadow-brutal">
            <p className="text-xs font-black uppercase tracking-[0.2em]">Knowledge base</p>
            <p className="mt-2 text-lg font-black">{activeChat?.title ?? '—'}</p>
          </div>
          <div className="rounded-[18px] border-4 border-black bg-paper p-3 shadow-brutal">
            <p className="text-xs font-black uppercase tracking-[0.2em]">Sources used</p>
            <p className="mt-2 text-lg font-black">{latestMetrics.retrieval_count ?? 0}</p>
          </div>
          <div className="rounded-[18px] border-4 border-black bg-paper p-3 shadow-brutal">
            <p className="text-xs font-black uppercase tracking-[0.2em]">Response speed</p>
            <p className="mt-2 text-lg font-black">{formatLatency(latestMetrics.latency_ms)}</p>
          </div>
          <div className="rounded-[18px] border-4 border-black bg-paper p-3 shadow-brutal">
            <p className="text-xs font-black uppercase tracking-[0.2em]">Embedding</p>
            <p className="mt-2 text-lg font-black">MiniLM</p>
          </div>
          <div className="rounded-[18px] border-4 border-black bg-paper p-3 shadow-brutal">
            <p className="text-xs font-black uppercase tracking-[0.2em]">Threshold</p>
            <p className="mt-2 text-lg font-black">0.2</p>
          </div>
          <div className="rounded-[18px] border-4 border-black bg-paper p-3 shadow-brutal">
            <p className="text-xs font-black uppercase tracking-[0.2em]">Top-k</p>
            <p className="mt-2 text-lg font-black">4</p>
          </div>
        </div>

        <div className="mt-4 rounded-[18px] border-4 border-black bg-white p-3 shadow-brutal">
          <p className="text-xs font-black uppercase tracking-[0.2em]">Guided prompts</p>
          <div className="mt-3 space-y-2">
            {guidedPrompts.map((prompt) => (
              <button
                key={prompt}
                type="button"
                className="w-full rounded-[14px] border-2 border-black bg-sky px-3 py-2 text-left text-sm font-bold shadow-brutal"
                onClick={() => setInput(prompt)}
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>
      </aside>
    </div>
  );
}
