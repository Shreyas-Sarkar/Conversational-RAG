# Deployment

## Prerequisites

Before deploying, you need:
- A [Supabase](https://supabase.com) project with the schema applied from `supabase/migrations/0001_init.sql`
- A [Pinecone](https://pinecone.io) serverless index: dimension `384`, metric `cosine`, cloud `aws`, region `us-east-1`
- A [Groq](https://console.groq.com) API key
- Node.js 18+ and pnpm 9+ (for frontend)
- Python 3.11+ (for backend)

---

## Option A — Vercel (Frontend) + Render (Backend)

This is the recommended cloud deployment for teams without container infrastructure.

### 1. Deploy the Backend to Render

1. Create a new **Web Service** on [Render](https://render.com).
2. Connect your GitHub repository and set the **root directory** to `backend`.
3. Set the **runtime** to Python 3.11.
4. Set the **start command**:
   ```
   uvicorn app.main:app --host 0.0.0.0 --port $PORT
   ```
5. Add all environment variables from `backend/.env.example`:

   | Key | Value |
   |---|---|
   | `SUPABASE_URL` | Your Supabase project URL |
   | `SUPABASE_ANON_KEY` | Supabase anon key |
   | `SUPABASE_SERVICE_ROLE_KEY` | Supabase service role key |
   | `PINECONE_API_KEY` | Pinecone API key |
   | `PINECONE_INDEX_NAME` | `conversational-rag` |
   | `PINECONE_CLOUD` | `aws` |
   | `PINECONE_REGION` | `us-east-1` |
   | `GROQ_API_KEY` | Groq API key |
   | `GROQ_MODEL_NAME` | `llama-3.3-70b-versatile` |
   | `GROQ_TEMPERATURE` | `0.2` |
   | `GROQ_TOP_P` | `0.9` |
   | `EMBEDDING_MODEL_NAME` | `sentence-transformers/all-MiniLM-L6-v2` |

6. Note the Render service URL (e.g., `https://conversational-rag-api.onrender.com`).

### 2. Deploy the Frontend to Vercel

1. Import your repository into [Vercel](https://vercel.com).
2. Set the **root directory** to `frontend`.
3. Set the **framework preset** to Next.js.
4. Add environment variables:

   | Key | Value |
   |---|---|
   | `NEXT_PUBLIC_SUPABASE_URL` | Your Supabase project URL |
   | `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key |
   | `NEXT_PUBLIC_API_BASE_URL` | Your Render backend URL |

5. Deploy. Vercel will build with `pnpm install && pnpm build` automatically.

### 3. Configure CORS

Update `backend/app/main.py` to add your Vercel frontend URL to `allow_origins`:

```python
allow_origins=[
    'http://localhost:3000',
    'https://your-app.vercel.app',
]
```

---

## Option B — Fly.io (Backend)

Fly.io is suitable for backends that need persistent warm instances without Render's cold-start delays.

1. Install the Fly CLI: `brew install flyctl`
2. From the `backend/` directory:
   ```bash
   fly launch --dockerfile ../docker/backend.Dockerfile
   ```
3. Set secrets:
   ```bash
   fly secrets set SUPABASE_URL=... PINECONE_API_KEY=... GROQ_API_KEY=...
   ```
4. Deploy:
   ```bash
   fly deploy
   ```

---

## Option C — Docker Compose (Self-hosted)

For self-hosted or internal deployments.

```bash
# From the repo root
cd docker
docker compose up --build
```

This starts:
- `frontend` on port 3000
- `backend` on port 8000

Environment variables must be supplied via a `.env` file at the repo root or via shell exports. The Docker setup does **not** bundle Supabase or Pinecone — you still need managed cloud accounts for those services.

---

## Supabase Setup Checklist

- [ ] Create a new Supabase project
- [ ] Open the SQL editor and run `supabase/migrations/0001_init.sql`
- [ ] Optionally run `supabase/seed.sql` for development seed data
- [ ] Optionally run `supabase/demo_seed.sql` for demo mode seed data
- [ ] Confirm RLS is enabled on all tables (the migration handles this)
- [ ] Copy `Project URL` and `anon key` from **Project Settings → API**
- [ ] Copy `service_role key` from **Project Settings → API** (keep secret)

## Pinecone Setup Checklist

- [ ] Create a new **serverless** index
- [ ] Name: `conversational-rag` (or set `PINECONE_INDEX_NAME` to match your name)
- [ ] Dimensions: `384`
- [ ] Metric: `cosine`
- [ ] Cloud: `aws`, Region: `us-east-1`
- [ ] Copy your API key

## Post-Deployment Verification

1. Hit `GET /health` — all three services (`groq`, `pinecone`, `supabase`) should return `"ok"`
2. Sign up for a new account via the UI
3. Create a chat and upload a PDF
4. Submit a query and verify the answer includes sources
5. Visit `/demo` and confirm demo chats load without authentication
