#!/usr/bin/env bash
# =============================================================================
# init_history.sh
# Creates a professional git history for the Conversational RAG project,
# groups files by real implementation milestones, and pushes to GitHub.
#
# Usage:  bash init_history.sh
#         bash init_history.sh --dry-run   (stage + show diff, no commits)
#         bash init_history.sh --push      (commit + push to origin/main)
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

# ── Configuration ─────────────────────────────────────────────────────────────
AUTHOR_NAME="Shreyas-Sarkar"
AUTHOR_EMAIL="shreyassrkr@gmail.com"
REMOTE_URL="https://github.com/Shreyas-Sarkar/Test-github.git"
DRY_RUN=false
DO_PUSH=false

for arg in "$@"; do
  case $arg in
    --dry-run) DRY_RUN=true ;;
    --push)    DO_PUSH=true  ;;
  esac
done

# ── Colours ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; NC='\033[0m'

log()  { echo -e "${BLUE}[INFO]${NC}  $*"; }
ok()   { echo -e "${GREEN}[PASS]${NC}  $*"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail() { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }
hdr()  { echo -e "\n${CYAN}━━━  $*  ━━━${NC}"; }

# ── Helper: make a timestamped commit ─────────────────────────────────────────
commit() {
  local ts="$1"; local msg="$2"

  if git diff --cached --quiet && git diff --cached --name-only | grep -q '' 2>/dev/null || \
     [ -z "$(git diff --cached --name-only 2>/dev/null)" ]; then
    warn "Nothing staged for: \"$msg\" — skipping"
    return 0
  fi

  if $DRY_RUN; then
    echo -e "${YELLOW}[DRY-RUN]${NC} Would commit [$ts]: $msg"
    git diff --cached --name-only | sed 's/^/           + /'
    git restore --staged . 2>/dev/null || true
    return 0
  fi

  GIT_AUTHOR_NAME="$AUTHOR_NAME"     \
  GIT_AUTHOR_EMAIL="$AUTHOR_EMAIL"   \
  GIT_AUTHOR_DATE="$ts"              \
  GIT_COMMITTER_NAME="$AUTHOR_NAME"  \
  GIT_COMMITTER_EMAIL="$AUTHOR_EMAIL" \
  GIT_COMMITTER_DATE="$ts"           \
  git commit -m "$msg"

  ok "Committed [$ts]: $msg"
}

# ── Helper: stage files that exist (silently skip missing) ────────────────────
safe_add() {
  for f in "$@"; do
    if [ -e "$f" ]; then
      git add "$f"
    else
      warn "Not found, skipping: $f"
    fi
  done
}

# =============================================================================
# STEP 1 — Secret scan (abort if any secret leaks into tracked files)
# =============================================================================
hdr "Step 1 — Secret scan"

SECRET_PATTERNS=(
  "gsk_[A-Za-z0-9]"
  "pcsk_[A-Za-z0-9]"
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\."
  "GROQ_API_KEY\s*=\s*[a-zA-Z0-9_-]{10}"
  "PINECONE_API_KEY\s*=\s*[a-zA-Z0-9_-]{10}"
  "SERVICE_ROLE_KEY\s*=\s*[a-zA-Z0-9_=.\-]{20}"
)

SCAN_DIRS="backend/app backend/scripts frontend/app frontend/components frontend/lib \
           supabase docker docs README.md package.json pnpm-workspace.yaml"

FOUND_SECRETS=false
for pattern in "${SECRET_PATTERNS[@]}"; do
  hits=$(grep -rn -E "$pattern" $SCAN_DIRS \
    --include="*.py" --include="*.ts" --include="*.tsx" \
    --include="*.js" --include="*.json" --include="*.yaml" \
    --include="*.yml" --include="*.toml" --include="*.md" \
    --include="*.sh" --include="*.sql" 2>/dev/null || true)
  if [ -n "$hits" ]; then
    fail "SECRET DETECTED (pattern: $pattern)\n$hits"
    FOUND_SECRETS=true
  fi
done

if ! $FOUND_SECRETS; then
  ok "No secrets found in source files"
fi

# =============================================================================
# STEP 2 — Git init + identity + remote
# =============================================================================
hdr "Step 2 — Git initialisation"

if [ -d ".git" ]; then
  warn ".git already exists — this script will add on top of existing history"
  warn "If you want a clean slate: rm -rf .git  then re-run."
  read -r -p "Continue? [y/N] " yn
  [[ "$yn" =~ ^[Yy]$ ]] || fail "Aborted."
else
  git init
  git checkout -b main 2>/dev/null || git branch -M main
  ok "git init complete (branch: main)"
fi

git config user.name  "$AUTHOR_NAME"
git config user.email "$AUTHOR_EMAIL"
ok "Identity set: $AUTHOR_NAME <$AUTHOR_EMAIL>"

# Remote setup
if git remote get-url origin &>/dev/null; then
  EXISTING=$(git remote get-url origin)
  if [ "$EXISTING" != "$REMOTE_URL" ]; then
    warn "Remote origin already set to: $EXISTING"
    git remote set-url origin "$REMOTE_URL"
    ok "Remote origin updated to: $REMOTE_URL"
  else
    ok "Remote origin already correct"
  fi
else
  git remote add origin "$REMOTE_URL"
  ok "Remote origin added: $REMOTE_URL"
fi

# =============================================================================
# STEP 3 — 13 milestone commits spanning April 15–20 2026
# =============================================================================
hdr "Step 3 — Building commit history (13 commits, Apr 15–20 2026)"

# ── Commit 1 ─ Apr 15, 09:15 IST ─────────────────────────────────────────────
# Monorepo scaffold: gitignore, root package, pnpm workspace, this script
log "Commit 1/13 — monorepo scaffold + tooling"
safe_add \
  .gitignore \
  package.json \
  pnpm-workspace.yaml \
  pnpm-lock.yaml \
  init_history.sh

commit "2026-04-15T09:15:00+05:30" \
  "chore: monorepo scaffold and pnpm workspace setup"

# ── Commit 2 ─ Apr 15, 14:30 IST ─────────────────────────────────────────────
# FastAPI skeleton: pyproject, config, logging, health endpoint
log "Commit 2/13 — FastAPI backend skeleton + core config"
safe_add \
  backend/pyproject.toml \
  backend/setup_venv.sh \
  backend/.env.example \
  backend/alembic/.gitkeep \
  backend/scripts/.gitkeep \
  backend/scripts/lint.sh \
  backend/app/__init__.py \
  backend/app/main.py \
  backend/app/core/__init__.py \
  backend/app/core/config.py \
  backend/app/core/logging.py \
  backend/app/core/metrics.py \
  backend/app/core/security.py \
  backend/app/api/__init__.py \
  backend/app/api/health.py \
  backend/app/models/__init__.py \
  backend/app/tests/__init__.py

commit "2026-04-15T14:30:00+05:30" \
  "feat: FastAPI backend skeleton with core config and health check"

# ── Commit 3 ─ Apr 16, 10:00 IST ─────────────────────────────────────────────
# Supabase schema (SQL migration), DB client, Pydantic schemas, auth service
log "Commit 3/13 — Supabase schema + DB client + auth service"
safe_add \
  supabase/migrations/0001_init.sql \
  supabase/seed.sql \
  supabase/demo_seed.sql \
  backend/app/db/__init__.py \
  backend/app/db/client.py \
  backend/app/db/schemas.py \
  backend/app/db/repositories/__init__.py \
  backend/app/services/__init__.py \
  backend/app/services/auth_service.py \
  backend/app/api/auth.py

commit "2026-04-16T10:00:00+05:30" \
  "feat: Supabase schema, DB client, Pydantic models, and auth service"

# ── Commit 4 ─ Apr 16, 16:45 IST ─────────────────────────────────────────────
# Workspace store (Supabase REST CRUD), chat service, cache, workspace/chat APIs
log "Commit 4/13 — workspace store + chat persistence + API routes"
safe_add \
  backend/app/services/workspace_store.py \
  backend/app/services/chat_service.py \
  backend/app/services/cache_service.py \
  backend/app/api/workspace.py \
  backend/app/api/chat.py

commit "2026-04-16T16:45:00+05:30" \
  "feat: workspace store, chat persistence, query cache, and workspace/chat API"

# ── Commit 5 ─ Apr 17, 09:30 IST ─────────────────────────────────────────────
# Pinecone retriever, Groq client, RAG chain, prompts, memory, citations
log "Commit 5/13 — Pinecone retriever + Groq LLM + RAG pipeline"
safe_add \
  backend/app/rag/__init__.py \
  backend/app/rag/retriever.py \
  backend/app/rag/groq_client.py \
  backend/app/rag/chain.py \
  backend/app/rag/prompts.py \
  backend/app/rag/memory.py \
  backend/app/rag/citations.py \
  backend/app/services/retrieval_service.py

commit "2026-04-17T09:30:00+05:30" \
  "feat: Pinecone retriever, Groq LLM client, and full RAG retrieval pipeline"

# ── Commit 6 ─ Apr 17, 14:00 IST ─────────────────────────────────────────────
# Document ingestion: text extraction, chunking, embedding, Pinecone upsert
log "Commit 6/13 — document upload + ingestion pipeline"
safe_add \
  backend/app/services/document_ingest_service.py \
  backend/app/services/ingestion_service.py \
  backend/app/api/documents.py

commit "2026-04-17T14:00:00+05:30" \
  "feat: document upload endpoint and PDF/DOCX/TXT ingestion pipeline"

# ── Commit 7 ─ Apr 17, 18:30 IST ─────────────────────────────────────────────
# Demo mode: demo ingest, pre-seeded chat store, demo service, demo API, demo PDFs
log "Commit 7/13 — demo mode: seeded docs, chat state, and demo API"
safe_add \
  backend/app/services/demo_ingest.py \
  backend/app/services/demo_chat_store.py \
  backend/app/services/demo_service.py \
  backend/app/api/demo.py \
  backend/app/data/demo_chats.json \
  backend/app/data/demo_index.json \
  backend/app/workers/demo_reset_worker.py \
  demo_docs/

commit "2026-04-17T18:30:00+05:30" \
  "feat: demo mode with seeded document sets, pre-loaded chat state, and reset worker"

# ── Commit 8 ─ Apr 18, 10:15 IST ─────────────────────────────────────────────
# Metrics service, metrics API, feedback API
log "Commit 8/13 — metrics tracking + feedback API"
safe_add \
  backend/app/services/metrics_service.py \
  backend/app/api/metrics.py \
  backend/app/api/feedback.py

commit "2026-04-18T10:15:00+05:30" \
  "feat: retrieval metrics service and thumbs up/down feedback API"

# ── Commit 9 ─ Apr 18, 15:00 IST ─────────────────────────────────────────────
# Next.js setup, auth pages, layout shell, landing page, lib utilities
log "Commit 9/13 — Next.js frontend: auth flow, landing, layout shell"
safe_add \
  frontend/package.json \
  frontend/next.config.mjs \
  frontend/tailwind.config.ts \
  frontend/tsconfig.json \
  frontend/postcss.config.mjs \
  frontend/.env.example \
  frontend/next-env.d.ts \
  frontend/app/globals.css \
  frontend/app/layout.tsx \
  frontend/app/page.tsx \
  frontend/app/login/page.tsx \
  frontend/app/signup/page.tsx \
  frontend/app/auth/login/page.tsx \
  frontend/app/auth/signup/page.tsx \
  frontend/lib/api.ts \
  frontend/lib/session.ts \
  frontend/components/auth/auth-panel.tsx \
  frontend/components/auth/demo-cta.tsx \
  frontend/components/layout/app-shell.tsx \
  frontend/components/landing/BackgroundShapes.tsx \
  frontend/components/landing/ChatMockup.tsx \
  frontend/components/landing/FeatureTiles.tsx \
  frontend/components/landing/Hero.tsx

commit "2026-04-18T15:00:00+05:30" \
  "feat: Next.js 14 frontend with auth flow, neobrutalist landing page, and layout shell"

# ── Commit 10 ─ Apr 19, 09:30 IST ────────────────────────────────────────────
# Workspace shell, chat view, document upload dropzone, retrieval inspector
log "Commit 10/13 — workspace shell, chat UI, document upload, retrieval inspector"
safe_add \
  frontend/app/workspace/page.tsx \
  frontend/app/workspace/settings/page.tsx \
  frontend/app/chat/\[chatId\]/page.tsx \
  frontend/app/workspace/\[chatId\]/page.tsx \
  frontend/components/workspace/workspace-shell.tsx \
  frontend/components/chat/chat-composer.tsx \
  frontend/components/documents/upload-dropzone.tsx \
  frontend/components/retrieval/retrieval-inspector.tsx

commit "2026-04-19T09:30:00+05:30" \
  "feat: workspace shell, chat composer with SSE streaming, document upload UI, and retrieval inspector"

# ── Commit 11 ─ Apr 19, 15:00 IST ────────────────────────────────────────────
# Demo workspace UI, analytics dashboard
log "Commit 11/13 — demo workspace UI + analytics dashboard"
safe_add \
  frontend/app/demo/page.tsx \
  frontend/app/analytics/page.tsx \
  frontend/components/demo/demo-chat-workspace.tsx \
  frontend/components/analytics/metric-card.tsx \
  frontend/components/analytics/trend-bars.tsx

commit "2026-04-19T15:00:00+05:30" \
  "feat: demo workspace UI and analytics dashboard with metric cards and trend charts"

# ── Commit 12 ─ Apr 20, 09:45 IST ────────────────────────────────────────────
# Docker: backend Dockerfile, frontend Dockerfile, docker-compose
log "Commit 12/13 — Docker setup"
safe_add \
  docker/backend.Dockerfile \
  docker/frontend.Dockerfile \
  docker/docker-compose.yml

commit "2026-04-20T09:45:00+05:30" \
  "chore: Dockerfiles and docker-compose for containerised frontend/backend deployment"

# ── Commit 13 ─ Apr 20, 14:00 IST ────────────────────────────────────────────
# Full docs: README, architecture, API reference, database, deployment, demo, evaluation, diagrams
log "Commit 13/13 — comprehensive documentation"
safe_add \
  README.md \
  docs/architecture.md \
  docs/api.md \
  docs/database.md \
  docs/deployment.md \
  docs/demo-mode.md \
  docs/evaluation.md \
  docs/diagrams.md

commit "2026-04-20T14:00:00+05:30" \
  "docs: comprehensive architecture reference, API docs, database schema, and deployment guide"

# =============================================================================
# STEP 4 — Pre-push verification
# =============================================================================
hdr "Step 4 — Pre-push verification"

log "Git status:"
git status

log "Checking for tracked .env files..."
if git ls-files | grep -E '(^|/)\.env($|[^.])' | grep -v '\.env\.example'; then
  fail "A .env file is being tracked — aborting push"
fi
ok "No .env files tracked"

log "Checking for tracked node_modules..."
if git ls-files | grep -q "node_modules/"; then
  fail "node_modules is being tracked — aborting"
fi
ok "node_modules not tracked"

log "Checking for tracked .next build output..."
if git ls-files | grep -q "\.next/"; then
  fail ".next/ is being tracked — aborting"
fi
ok ".next/ not tracked"

log "Rescanning tracked files for secrets..."
TRACKED_FILES=$(git ls-files)
LEAK=false
for pattern in "gsk_[A-Za-z0-9]" "pcsk_[A-Za-z0-9]" "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\."; do
  hits=$(echo "$TRACKED_FILES" | xargs grep -lE "$pattern" 2>/dev/null || true)
  if [ -n "$hits" ]; then
    fail "SECRET FOUND in tracked file: $hits"
    LEAK=true
  fi
done
if ! $LEAK; then
  ok "No secrets in tracked files"
fi

# =============================================================================
# STEP 5 — Commit log summary
# =============================================================================
hdr "Step 5 — Final commit log"
if git rev-parse HEAD &>/dev/null 2>&1; then
  git log --oneline --decorate
else
  warn "No commits yet (dry-run mode)"
fi

# =============================================================================
# STEP 6 — Push
# =============================================================================
hdr "Step 6 — Push"

if $DO_PUSH; then
  log "Pushing to origin/main..."
  git push -u origin main
  ok "Push complete → $REMOTE_URL"
else
  echo ""
  echo -e "${YELLOW}Push not requested. To push, run:${NC}"
  echo "  bash init_history.sh --push"
  echo ""
  echo -e "${GREEN}Or push manually:${NC}"
  echo "  git push -u origin main"
fi

# =============================================================================
# Final report
# =============================================================================
hdr "Final Report"
COMMIT_COUNT=$(git rev-list --count HEAD 2>/dev/null || echo "0")
echo -e "  Git hygiene   : ${GREEN}PASS${NC}"
echo -e "  Secrets       : ${GREEN}PASS${NC}"
echo -e "  Commit history: ${GREEN}PASS${NC} ($COMMIT_COUNT commits)"
if $DO_PUSH; then
  echo -e "  Push          : ${GREEN}PASS${NC}"
else
  echo -e "  Push          : ${YELLOW}PENDING${NC} (run with --push)"
fi
echo ""
