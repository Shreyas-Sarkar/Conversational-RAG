create extension if not exists pgcrypto;

create table if not exists users (
  id uuid primary key references auth.users(id) on delete cascade,
  name text not null,
  email text unique not null,
  is_demo boolean not null default false,
  created_at timestamptz not null default now()
);

create table if not exists chats (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  title text not null,
  pinned boolean not null default false,
  memory_summary text,
  is_demo boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists messages (
  id uuid primary key default gen_random_uuid(),
  chat_id uuid not null references chats(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  role text not null check (role in ('user', 'assistant', 'system')),
  content text not null,
  sources jsonb not null default '[]'::jsonb,
  latency_ms integer,
  token_count integer,
  retrieval_count integer,
  prompt_version text,
  created_at timestamptz not null default now()
);

create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  chat_id uuid not null references chats(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  filename text not null,
  display_name text,
  original_filename text,
  file_type text not null,
  file_size_bytes bigint not null,
  status text not null check (status in ('uploaded', 'chunking', 'embedding', 'indexing', 'ready', 'failed')),
  pinecone_namespace text not null,
  chunk_count integer not null default 0,
  error_message text,
  is_demo boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists feedback (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null references messages(id) on delete cascade,
  user_id uuid not null references users(id) on delete cascade,
  rating integer not null check (rating in (-1, 1)),
  comment text,
  created_at timestamptz not null default now()
);

create table if not exists query_cache (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  chat_id uuid not null references chats(id) on delete cascade,
  query_hash text not null,
  response_text text not null,
  sources jsonb not null default '[]'::jsonb,
  ttl_expires_at timestamptz not null,
  created_at timestamptz not null default now()
);

create table if not exists retrieval_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  chat_id uuid not null references chats(id) on delete cascade,
  message_id uuid references messages(id) on delete cascade,
  top_k integer not null,
  threshold numeric(3,2) not null,
  retrieved_chunks integer not null,
  latency_ms integer not null,
  tokens integer not null,
  confidence numeric(3,2) not null,
  created_at timestamptz not null default now()
);

create table if not exists demo_reset_runs (
  id uuid primary key default gen_random_uuid(),
  run_at timestamptz not null default now(),
  chats_reset integer not null,
  documents_restored integer not null,
  analytics_restored jsonb not null default '{}'::jsonb,
  status text not null check (status in ('started', 'success', 'failed')),
  error_message text
);

create index if not exists chats_user_id_created_at_idx on chats (user_id, created_at desc);
create index if not exists messages_chat_id_created_at_idx on messages (chat_id, created_at desc);
create index if not exists documents_chat_id_status_idx on documents (chat_id, status);
create index if not exists feedback_message_id_idx on feedback (message_id);
create index if not exists query_cache_user_id_chat_id_query_hash_idx on query_cache (user_id, chat_id, query_hash);
create index if not exists retrieval_events_user_id_created_at_idx on retrieval_events (user_id, created_at desc);
create index if not exists demo_reset_runs_run_at_idx on demo_reset_runs (run_at desc);

create or replace function set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists set_chats_updated_at on chats;
create trigger set_chats_updated_at
before update on chats
for each row
execute function set_updated_at();

drop trigger if exists set_documents_updated_at on documents;
create trigger set_documents_updated_at
before update on documents
for each row
execute function set_updated_at();

alter table users enable row level security;
alter table chats enable row level security;
alter table messages enable row level security;
alter table documents enable row level security;
alter table feedback enable row level security;
alter table query_cache enable row level security;
alter table retrieval_events enable row level security;

drop policy if exists users_select_own on users;
create policy users_select_own on users
for select using (id = auth.uid());

drop policy if exists users_insert_own on users;
create policy users_insert_own on users
for insert with check (id = auth.uid());

drop policy if exists users_update_own on users;
create policy users_update_own on users
for update using (id = auth.uid()) with check (id = auth.uid());

drop policy if exists chats_crud_own on chats;
create policy chats_crud_own on chats
for all using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists messages_crud_own on messages;
create policy messages_crud_own on messages
for all using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists documents_crud_own on documents;
create policy documents_crud_own on documents
for all using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists feedback_crud_own on feedback;
create policy feedback_crud_own on feedback
for all using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists query_cache_crud_own on query_cache;
create policy query_cache_crud_own on query_cache
for all using (user_id = auth.uid()) with check (user_id = auth.uid());

drop policy if exists retrieval_events_select_own on retrieval_events;
create policy retrieval_events_select_own on retrieval_events
for select using (user_id = auth.uid());

drop policy if exists retrieval_events_insert_own on retrieval_events;
create policy retrieval_events_insert_own on retrieval_events
for insert with check (user_id = auth.uid());
