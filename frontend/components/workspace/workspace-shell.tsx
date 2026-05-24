'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useRef, useState } from 'react';

import { getApiBaseUrl } from '@/lib/api';
import { clearStoredAuth, readStoredAuth, type StoredAuth } from '@/lib/session';

type WorkspaceChat = {
  id: string;
  user_id: string;
  title: string;
  pinned?: boolean;
  memory_summary?: string | null;
  namespace?: string | null;
  is_demo?: boolean;
  created_at?: string | null;
  updated_at?: string | null;
  message_count?: number;
  document_count?: number;
};

type WorkspaceDocument = {
  id: string;
  chat_id: string;
  user_id: string;
  display_name?: string;
  original_filename?: string;
  filename: string;
  file_type: string;
  file_size_bytes: number;
  status: string;
  pinecone_namespace: string;
  chunk_count: number;
  error_message?: string | null;
  is_demo?: boolean;
  created_at?: string | null;
  updated_at?: string | null;
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
  cache_hit?: boolean;
  memory_summary?: string;
};

type WorkspaceBootstrap = {
  user: { id: string; name: string; email: string; created_at?: string };
  chats: WorkspaceChat[];
  metrics: {
    chat_count?: number;
    document_count?: number;
    message_count?: number;
    cache_entries?: number;
  };
  default_chat_id?: string | null;
  profile_menu?: Array<{ label: string; href?: string; action?: string }>;
};

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(payload?.detail ?? payload?.error ?? `Request failed: ${response.status}`);
  }
  return payload as T;
}

function formatLatency(latencyMs?: number) {
  if (!latencyMs) {
    return '0.0 sec';
  }
  return `${(latencyMs / 1000).toFixed(1)} sec`;
}

function bytesToBase64(buffer: ArrayBuffer) {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  for (let index = 0; index < bytes.length; index += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(index, index + chunkSize));
  }
  return window.btoa(binary);
}

function looksLikeStorageName(value: string) {
  return /^(?:[a-f0-9]{16,}|[a-f0-9-]{32,})(?:\.[a-z0-9]+)?$/i.test(value.trim());
}

function humanizeDocumentName(document: WorkspaceDocument) {
  const rawName = document.display_name || document.original_filename || document.filename;
  if (looksLikeStorageName(rawName)) {
    return 'Uploaded document';
  }
  const [baseName, extension] = rawName.split(/\.(?=[^.]+$)/);
  const readableBase = baseName
    .replace(/[_-]+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
    .replace(/\b\w/g, (character) => character.toUpperCase());
  return extension ? `${readableBase}.${extension}` : readableBase;
}

function formatRelativeTime(isoDate?: string | null) {
  if (!isoDate) return 'just now';
  const timestamp = new Date(isoDate).getTime();
  if (Number.isNaN(timestamp)) return 'just now';
  const diffSeconds = Math.max(1, Math.round((Date.now() - timestamp) / 1000));
  if (diffSeconds < 60) return `${diffSeconds}s ago`;
  const diffMinutes = Math.round(diffSeconds / 60);
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  const diffHours = Math.round(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.round(diffHours / 24);
  return `${diffDays}d ago`;
}

function formatPercent(value?: number) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '0%';
  return `${Math.round(value * 100)}%`;
}

function humanizeSourceName(name: string) {
  if (looksLikeStorageName(name)) {
    return 'Uploaded document';
  }
  return name.replace(/[_-]+/g, ' ').replace(/\s+/g, ' ').trim();
}

function sanitizeSummaryText(value: string) {
  const focusMatch = value.match(/focused on:\s*(.+)$/i);
  const text = (focusMatch?.[1] ?? value)
    .replace(/\bchat\s+[a-f0-9-]{8,}\b/gi, 'this chat')
    .replace(/\b[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9-]{12,}\b/gi, 'this workspace')
    .replace(/\s+/g, ' ')
    .trim();
  return text || 'Start a conversation to capture the recent topic.';
}

async function fileToUploadPayload(file: File) {
  const buffer = await file.arrayBuffer();
  return {
    filename: file.name,
    content_base64: bytesToBase64(buffer),
    mime_type: file.type || 'application/octet-stream',
    size_bytes: file.size
  };
}

export function WorkspaceShell({ initialChatId }: { initialChatId?: string }) {
  const router = useRouter();
  const endRef = useRef<HTMLDivElement | null>(null);
  const [auth, setAuth] = useState<StoredAuth | null>(null);
  const [bootstrap, setBootstrap] = useState<WorkspaceBootstrap | null>(null);
  const [chats, setChats] = useState<WorkspaceChat[]>([]);
  const [activeChatId, setActiveChatId] = useState('');
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [documents, setDocuments] = useState<WorkspaceDocument[]>([]);
  const [memorySummary, setMemorySummary] = useState('');
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [input, setInput] = useState('Summarize the uploaded documents');
  const [latestSources, setLatestSources] = useState<RetrievalSource[]>([]);
  const [latestMetrics, setLatestMetrics] = useState({
    namespace: '',
    retrieval_count: 0,
    latency_ms: 0,
    top_k: 4,
    threshold: 0.2,
    cache_hit: false
  });
  const [uploadStatus, setUploadStatus] = useState('');
  const [newChatTitle, setNewChatTitle] = useState('');
  const [isMobileDrawerOpen, setIsMobileDrawerOpen] = useState(false);

  const selectedChat = useMemo(() => chats.find((chat) => chat.id === activeChatId) ?? null, [activeChatId, chats]);
  const workspaceName = selectedChat?.title ?? bootstrap?.user.name ?? 'Workspace';
  const recentTopic = useMemo(() => {
    const lastUserMessage = [...messages].reverse().find((message) => message.role === 'user');
    if (lastUserMessage?.content) {
      return sanitizeSummaryText(lastUserMessage.content);
    }
    return memorySummary ? sanitizeSummaryText(memorySummary) : 'Start a conversation to capture the recent topic.';
  }, [memorySummary, messages]);
  const topSimilarity = latestSources.length ? Math.max(...latestSources.map((source) => source.similarity)) : 0;

  function renderChatSidebar(showHeading = true) {
    return (
      <>
        {showHeading ? (
          <div className="inline-flex -rotate-2 rounded-[14px] border-4 border-black bg-sun px-4 py-2 text-xs font-black uppercase tracking-[0.3em] shadow-brutal">
            Conversations
          </div>
        ) : null}

        <div className="mt-4 rounded-[18px] border-4 border-black bg-white p-4 shadow-brutal">
          <p className="text-xs font-black uppercase tracking-[0.2em]">Signed in</p>
          <h2 className="mt-2 text-xl font-black">{bootstrap?.user.name ?? auth?.user.name ?? 'Workspace user'}</h2>
          <p className="mt-1 text-sm font-medium text-gray-700">{bootstrap?.user.email ?? auth?.user.email}</p>
          <button
            className="mt-4 w-full rounded-[14px] border-4 border-black bg-coral px-4 py-3 text-sm font-black uppercase tracking-[0.08em] shadow-brutal"
            onClick={signOut}
            type="button"
          >
            Sign out
          </button>
        </div>

        <div className="mt-4 flex items-center gap-3">
          <input
            className="min-w-0 flex-1 rounded-[14px] border-4 border-black bg-white px-3 py-2 text-sm font-medium outline-none shadow-brutal"
            placeholder="New conversation"
            value={newChatTitle}
            onChange={(event) => setNewChatTitle(event.target.value)}
          />
          <button
            className="rounded-[14px] border-4 border-black bg-paper px-3 py-2 text-sm font-black uppercase shadow-brutal"
            onClick={createChat}
            type="button"
          >
            Add
          </button>
        </div>

        <div className="mt-4 space-y-3">
          {chats.map((chat) => {
            const isActive = chat.id === activeChatId;
            return (
              <button
                key={chat.id}
                type="button"
                onClick={() => {
                  setIsMobileDrawerOpen(false);
                  switchChat(chat);
                }}
                className={`w-full rounded-[18px] border-4 border-black px-4 py-3 text-left shadow-brutal transition-transform hover:-translate-x-1 hover:-translate-y-1 ${
                  isActive ? 'bg-coral' : 'bg-white'
                }`}
              >
                <div className="text-xs font-black uppercase tracking-[0.2em]">{isActive ? 'Active' : 'Chat'}</div>
                <div className="mt-1 text-lg font-black leading-6">{chat.title}</div>
                <div className="mt-2 text-xs font-bold opacity-80">
                  {chat.document_count ?? 0} docs · {chat.message_count ?? 0} turns
                </div>
              </button>
            );
          })}
        </div>

        <div className="mt-4 rounded-[18px] border-4 border-black bg-paper p-4 shadow-brutal">
          <p className="text-xs font-black uppercase tracking-[0.2em]">Workspace focus</p>
          <p className="mt-2 text-sm font-medium leading-6 text-gray-800">Each conversation keeps its own documents and retrieval context together.</p>
        </div>

        <div className="mt-4 rounded-[18px] border-4 border-black bg-white p-4 shadow-brutal">
          <Link className="block rounded-[14px] border-4 border-black bg-sun px-4 py-3 text-center font-black uppercase shadow-brutal" href="/demo">
            Open demo mode
          </Link>
        </div>
      </>
    );
  }

  useEffect(() => {
    const stored = readStoredAuth();
    if (!stored?.session?.token) {
      router.replace('/auth/login');
      return;
    }

    setAuth(stored);
  }, [router]);

  useEffect(() => {
    if (!auth?.session?.token) {
      return;
    }

    let cancelled = false;
    (async () => {
      try {
        const payload = await fetchJson<{ data: WorkspaceBootstrap }>(`${getApiBaseUrl()}/workspace/bootstrap?session_token=${encodeURIComponent(auth.session.token)}`, {
          method: 'GET',
          cache: 'no-store'
        });
        if (cancelled) return;

        setBootstrap(payload.data);
        setChats(payload.data.chats ?? []);
        const defaultChatId = initialChatId || payload.data.default_chat_id || payload.data.chats?.[0]?.id || '';
        setActiveChatId(defaultChatId);
      } catch {
        if (!cancelled) {
          clearStoredAuth();
          router.replace('/auth/login');
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [auth?.session?.token, initialChatId, router]);

  useEffect(() => {
    if (!activeChatId) {
      return;
    }

    let cancelled = false;
    setIsLoadingHistory(true);

    (async () => {
      try {
        const [historyPayload, documentsPayload] = await Promise.all([
          fetchJson<{ data: { memory_summary: string; messages: ChatMessage[] } }>(
            `${getApiBaseUrl()}/chat-history?chat_id=${encodeURIComponent(activeChatId)}`,
            { method: 'GET', cache: 'no-store' }
          ),
          fetchJson<{ data: { documents: WorkspaceDocument[] } }>(
            `${getApiBaseUrl()}/documents?chat_id=${encodeURIComponent(activeChatId)}`,
            { method: 'GET', cache: 'no-store' }
          )
        ]);

        if (cancelled) return;
        setMessages(historyPayload.data.messages ?? []);
        setMemorySummary(historyPayload.data.memory_summary ?? '');
        setDocuments(documentsPayload.data.documents ?? []);
      } catch {
        if (!cancelled) {
          setMessages([]);
          setMemorySummary('');
          setDocuments([]);
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
  }, [activeChatId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingText]);

  async function refreshChats(nextActiveChatId?: string) {
    if (!auth?.session?.token) return;
    const payload = await fetchJson<{ data: { chats: WorkspaceChat[] } }>(`${getApiBaseUrl()}/workspace/chats?session_token=${encodeURIComponent(auth.session.token)}`, {
      method: 'GET',
      cache: 'no-store'
    });
    setChats(payload.data.chats ?? []);
    if (nextActiveChatId) {
      setActiveChatId(nextActiveChatId);
      router.push(`/workspace/${nextActiveChatId}`);
    }
  }

  async function switchChat(chat: WorkspaceChat) {
    setActiveChatId(chat.id);
    router.push(`/workspace/${chat.id}`);
  }

  async function createChat() {
    if (!auth?.session?.token) return;

    const title = newChatTitle.trim() || `Chat ${chats.length + 1}`;
    const payload = await fetchJson<{ data: { chat: WorkspaceChat } }>(`${getApiBaseUrl()}/workspace/chats`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_token: auth.session.token, title })
    });

    setNewChatTitle('');
    await refreshChats(payload.data.chat.id);
  }

  async function uploadFiles(files: FileList | null) {
    if (!files?.length || !auth?.session?.token || !activeChatId) {
      return;
    }

    setUploadStatus(`Uploading ${files.length} document${files.length > 1 ? 's' : ''}...`);
    for (const file of Array.from(files)) {
      const payload = await fileToUploadPayload(file);
      await fetchJson(`${getApiBaseUrl()}/upload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_token: auth.session.token,
          chat_id: activeChatId,
          ...payload
        })
      });
    }

    setUploadStatus('Upload complete');
    const documentsPayload = await fetchJson<{ data: { documents: WorkspaceDocument[] } }>(
      `${getApiBaseUrl()}/documents?chat_id=${encodeURIComponent(activeChatId)}`,
      { method: 'GET', cache: 'no-store' }
    );
    setDocuments(documentsPayload.data.documents ?? []);
    await refreshChats(activeChatId);
  }

  async function submitMessage(nextMessage: string) {
    if (!activeChatId || !nextMessage.trim()) return;

    const userMessage: ChatMessage = {
      id: `${activeChatId}-user-${Date.now()}`,
      role: 'user',
      content: nextMessage.trim(),
      sources: []
    };

    const optimisticMessages = [...messages, userMessage];
    setMessages(optimisticMessages);
    setInput('');
    setStreamingText('');
    setIsStreaming(true);
    setLatestSources([]);

    const response = await fetch(`${getApiBaseUrl()}/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: activeChatId,
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
          const parsed = JSON.parse(dataLine.slice(6)) as { type: 'token' | 'final'; value: any };

          if (parsed.type === 'token') {
            assistantDraft = `${assistantDraft}${parsed.value} `;
            setStreamingText(assistantDraft);
          }

          if (parsed.type === 'final') {
            hasFinalPayload = true;
            const finalPayload = parsed.value.data as QueryResult;
            setLatestSources(finalPayload.sources || []);
            setLatestMetrics({
              namespace: finalPayload.namespace ?? '',
              retrieval_count: finalPayload.retrieval_count ?? 0,
              latency_ms: finalPayload.latency_ms ?? 0,
              top_k: 4,
              threshold: 0.2,
              cache_hit: Boolean(finalPayload.cache_hit)
            });
            assistantDraft = finalPayload.answer;
            setStreamingText(finalPayload.answer);
            const assistantMessage: ChatMessage = {
              id: `${activeChatId}-assistant-${Date.now()}`,
              role: 'assistant',
              content: finalPayload.answer,
              sources: finalPayload.sources as Array<Record<string, unknown>>
            };
            const nextMessages = [...optimisticMessages, assistantMessage];
            setMessages(nextMessages);
          }
        }
      }
    } finally {
      setIsStreaming(false);
      setStreamingText('');
      if (!hasFinalPayload && assistantDraft) {
        const fallbackAssistant: ChatMessage = {
          id: `${activeChatId}-assistant-${Date.now()}`,
          role: 'assistant',
          content: assistantDraft.trim() || 'I could not generate a response.',
          sources: latestSources as Array<Record<string, unknown>>
        };
        setMessages([...optimisticMessages, fallbackAssistant]);
      }
    }
  }

  function signOut() {
    clearStoredAuth();
    router.push('/auth/login');
  }

  const documentCount = documents.length;
  const cacheStatus = latestMetrics.cache_hit ? 'Hit' : 'Miss';

  return (
    <div className="min-h-screen bg-[linear-gradient(135deg,_rgba(255,246,214,0.95)_0%,_rgba(244,244,244,1)_45%,_rgba(217,246,238,0.9)_100%)] p-4 lg:p-5">
      <div className="mb-4 flex items-center justify-between gap-3 rounded-[18px] border-4 border-black bg-white px-4 py-3 shadow-brutal lg:hidden">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.2em]">Workspace</p>
          <p className="text-sm font-bold">{workspaceName}</p>
        </div>
        <button
          className="rounded-[14px] border-4 border-black bg-sky px-4 py-2 text-sm font-black uppercase shadow-brutal"
          type="button"
          onClick={() => setIsMobileDrawerOpen(true)}
        >
          Menu
        </button>
      </div>

      <div className="grid min-h-[calc(100vh-2rem)] grid-cols-1 gap-4 md:grid-cols-[minmax(0,1fr)_22rem] lg:grid-cols-[18rem_minmax(0,1fr)_22rem]">
        <aside className="hidden rounded-[18px] border-4 border-black bg-sky p-4 shadow-brutal lg:block">
          {renderChatSidebar()}
        </aside>

        {isMobileDrawerOpen ? (
          <div className="fixed inset-0 z-50 bg-black/50 p-4 lg:hidden" onClick={() => setIsMobileDrawerOpen(false)}>
            <aside className="h-full max-h-[calc(100vh-2rem)] overflow-y-auto rounded-[24px] border-4 border-black bg-sky p-4 shadow-brutal" onClick={(event) => event.stopPropagation()}>
              <div className="mb-4 flex items-center justify-between">
                <div className="inline-flex -rotate-2 rounded-[14px] border-4 border-black bg-sun px-4 py-2 text-xs font-black uppercase tracking-[0.3em] shadow-brutal">
                  Conversations
                </div>
                <button className="rounded-[14px] border-4 border-black bg-white px-3 py-2 text-sm font-black uppercase shadow-brutal" type="button" onClick={() => setIsMobileDrawerOpen(false)}>
                  Close
                </button>
              </div>
              {renderChatSidebar(false)}
            </aside>
          </div>
        ) : null}

        <main className="rounded-[18px] border-4 border-black bg-white p-4 shadow-brutal">
          <div className="flex flex-wrap items-start justify-between gap-4 border-b-4 border-black pb-4">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.22em]">ACTIVE CHAT</p>
              <h1 className="mt-2 text-3xl font-black uppercase tracking-[-0.03em]">{workspaceName}</h1>
              <p className="mt-2 text-sm font-medium text-gray-700">{documentCount} documents</p>
              <p className="mt-2 text-sm font-medium text-gray-700">Focused on: {memorySummary ? sanitizeSummaryText(memorySummary) : recentTopic}</p>
              <p className="mt-2 text-sm font-medium text-gray-700">Recent topic: {recentTopic}</p>
            </div>
            <div className="rounded-[14px] border-4 border-black bg-paper px-4 py-3 text-sm font-black uppercase tracking-[0.16em] shadow-brutal">
              {documentCount} documents
            </div>
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
                placeholder="Compare the uploaded documents..."
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

        <aside className="sticky top-5 rounded-[18px] border-4 border-black bg-moss p-4 shadow-brutal lg:self-start">
          <div className="inline-flex -rotate-2 rounded-[12px] border-2 border-black bg-sun px-3 py-1 text-[11px] font-black uppercase tracking-[0.22em] shadow-brutal">
            Workspace modules
          </div>

          <div className="mt-4 grid gap-4">
            <section className="rounded-[18px] border-4 border-black bg-paper p-4 shadow-brutal">
              <p className="text-xs font-black uppercase tracking-[0.2em]">Workspace status</p>
              <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-[14px] border-2 border-black bg-white p-3 shadow-brutal">
                  <p className="text-[11px] font-black uppercase tracking-[0.2em]">Messages</p>
                  <p className="mt-2 text-lg font-black">{bootstrap?.metrics.message_count ?? 0}</p>
                </div>
                <div className="rounded-[14px] border-2 border-black bg-white p-3 shadow-brutal">
                  <p className="text-[11px] font-black uppercase tracking-[0.2em]">Documents indexed</p>
                  <p className="mt-2 text-lg font-black">{bootstrap?.metrics.document_count ?? documentCount}</p>
                </div>
                <div className="rounded-[14px] border-2 border-black bg-white p-3 shadow-brutal">
                  <p className="text-[11px] font-black uppercase tracking-[0.2em]">Response speed</p>
                  <p className="mt-2 text-lg font-black">{formatLatency(latestMetrics.latency_ms)}</p>
                </div>
                <div className="rounded-[14px] border-2 border-black bg-white p-3 shadow-brutal">
                  <p className="text-[11px] font-black uppercase tracking-[0.2em]">Cache</p>
                  <p className="mt-2 text-lg font-black">{cacheStatus}</p>
                </div>
              </div>
            </section>

            <section className="rounded-[18px] border-4 border-black bg-white p-4 shadow-brutal">
              <p className="text-xs font-black uppercase tracking-[0.2em]">Documents</p>
              <div className="mt-3 space-y-3">
                {documents.map((document) => (
                  <article key={document.id} className="rounded-[16px] border-2 border-black bg-sky p-3 shadow-brutal">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="min-w-0 break-words font-black leading-6">{humanizeDocumentName(document)}</p>
                        <p className="mt-1 text-xs font-bold uppercase tracking-[0.18em]">{String(document.status).toUpperCase()}</p>
                      </div>
                      <div className="text-right text-xs font-bold uppercase tracking-[0.18em]">
                        <p>{document.chunk_count} chunks</p>
                        <p className="mt-1">{formatRelativeTime(document.created_at)}</p>
                      </div>
                    </div>
                  </article>
                ))}
                {!documents.length ? <div className="rounded-[14px] border-2 border-black bg-paper px-3 py-2 text-sm font-bold shadow-brutal">No documents yet</div> : null}
              </div>
            </section>

            <section className="rounded-[18px] border-4 border-black bg-white p-4 shadow-brutal">
              <p className="text-xs font-black uppercase tracking-[0.2em]">Upload</p>
              <p className="mt-2 text-sm font-medium leading-6 text-gray-800">Drop documents into the active conversation to expand the knowledge base.</p>
              <label className="mt-3 block cursor-pointer rounded-[16px] border-4 border-dashed border-black bg-paper p-4 text-center shadow-brutal">
                <input className="hidden" multiple type="file" onChange={(event) => void uploadFiles(event.target.files)} />
                <div className="text-lg font-black uppercase tracking-[0.12em]">Drop or browse</div>
                <p className="mt-1 text-sm font-medium">PDF, TXT, and DOCX uploads</p>
              </label>
              {uploadStatus ? <p className="mt-3 text-sm font-bold">{uploadStatus}</p> : null}
            </section>

            <section className="rounded-[18px] border-4 border-black bg-white p-4 shadow-brutal">
              <p className="text-xs font-black uppercase tracking-[0.2em]">Retrieval</p>
              <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-[14px] border-2 border-black bg-paper p-3 shadow-brutal">
                  <p className="text-[11px] font-black uppercase tracking-[0.2em]">Top-k</p>
                  <p className="mt-2 text-lg font-black">{latestMetrics.top_k}</p>
                </div>
                <div className="rounded-[14px] border-2 border-black bg-paper p-3 shadow-brutal">
                  <p className="text-[11px] font-black uppercase tracking-[0.2em]">Threshold</p>
                  <p className="mt-2 text-lg font-black">{latestMetrics.threshold.toFixed(1)}</p>
                </div>
                <div className="rounded-[14px] border-2 border-black bg-paper p-3 shadow-brutal">
                  <p className="text-[11px] font-black uppercase tracking-[0.2em]">Sources used</p>
                  <p className="mt-2 text-lg font-black">{latestMetrics.retrieval_count}</p>
                </div>
                <div className="rounded-[14px] border-2 border-black bg-paper p-3 shadow-brutal">
                  <p className="text-[11px] font-black uppercase tracking-[0.2em]">Similarity</p>
                  <p className="mt-2 text-lg font-black">{formatPercent(topSimilarity)}</p>
                </div>
              </div>
            </section>

            <section className="rounded-[18px] border-4 border-black bg-white p-4 shadow-brutal">
              <p className="text-xs font-black uppercase tracking-[0.2em]">Profile</p>
              <div className="mt-3 space-y-2">
                {(bootstrap?.profile_menu ?? []).map((item) =>
                  item.href ? (
                    <Link key={item.label} href={item.href as any} className="block rounded-[14px] border-2 border-black bg-paper px-3 py-2 text-sm font-bold shadow-brutal">
                      {item.label}
                    </Link>
                  ) : (
                    <button key={item.label} type="button" onClick={item.action === 'logout' ? signOut : undefined} className="w-full rounded-[14px] border-2 border-black bg-paper px-3 py-2 text-left text-sm font-bold shadow-brutal">
                      {item.label}
                    </button>
                  )
                )}
              </div>
            </section>
          </div>
        </aside>
      </div>
    </div>
  );
}
