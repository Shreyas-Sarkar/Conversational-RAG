from datetime import datetime

from pydantic import BaseModel, Field


class UserRecord(BaseModel):
    id: str
    name: str
    email: str
    is_demo: bool = False
    created_at: datetime | None = None


class ChatRecord(BaseModel):
    id: str
    user_id: str
    title: str
    pinned: bool = False
    memory_summary: str | None = None
    is_demo: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MessageRecord(BaseModel):
    id: str
    chat_id: str
    user_id: str
    role: str
    content: str
    sources: list[dict[str, object]] = Field(default_factory=list)
    latency_ms: int | None = None
    token_count: int | None = None
    retrieval_count: int | None = None
    prompt_version: str | None = None
    created_at: datetime | None = None


class DocumentRecord(BaseModel):
    id: str
    chat_id: str
    user_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    status: str
    pinecone_namespace: str
    chunk_count: int = 0
    error_message: str | None = None
    is_demo: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class FeedbackRecord(BaseModel):
    id: str
    message_id: str
    user_id: str
    rating: int
    comment: str | None = None
    created_at: datetime | None = None


class QueryCacheRecord(BaseModel):
    id: str
    user_id: str
    chat_id: str
    query_hash: str
    response_text: str
    sources: list[dict[str, object]] = Field(default_factory=list)
    ttl_expires_at: datetime
    created_at: datetime | None = None


class RetrievalEventRecord(BaseModel):
    id: str
    user_id: str
    chat_id: str
    message_id: str | None = None
    top_k: int
    threshold: float
    retrieved_chunks: int
    latency_ms: int
    tokens: int
    confidence: float
    created_at: datetime | None = None


class DemoResetRunRecord(BaseModel):
    id: str
    run_at: datetime | None = None
    chats_reset: int
    documents_restored: int
    analytics_restored: dict[str, object] = Field(default_factory=dict)
    status: str
    error_message: str | None = None


class HealthResponse(BaseModel):
    status: str
    groq: str
    pinecone: str
    supabase: str


class ApiEnvelope(BaseModel):
    ok: bool = True
    data: dict[str, object] = Field(default_factory=dict)
    error: str | None = None
    request_id: str | None = None


class SeededChatSummary(BaseModel):
    id: str
    title: str
    document_count: int = 0
    pinned: bool = False


class DemoAnalyticsSnapshot(BaseModel):
    queries: int
    avg_latency: float
    feedback: float
    chunks: int


class DemoBootstrapData(BaseModel):
    mode: str = 'demo'
    session: dict[str, str] = Field(default_factory=dict)
    seeded_chats: list[SeededChatSummary]
    analytics: DemoAnalyticsSnapshot


class SignupResponseData(BaseModel):
    user: UserRecord
    session: dict[str, str] = Field(default_factory=dict)
    bootstrap_chat_id: str | None = None


class LoginResponseData(BaseModel):
    user: UserRecord
    session: dict[str, str] = Field(default_factory=dict)
    default_chat_ids: list[str] = Field(default_factory=list)


class RetrievalSourceRecord(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    chunk_index: int
    similarity: float
    chunk_text: str


class QueryResponseData(BaseModel):
    chat_id: str
    answer: str
    sources: list[RetrievalSourceRecord] = Field(default_factory=list)
    retrieval_count: int = 0
    confidence: float = 0.0
    latency_ms: int = 0
    used_llm: bool = False
    namespace: str | None = None
    cache_hit: bool = False


class ChatTurnResponseData(BaseModel):
    chat_id: str
    user_message_id: str
    assistant_message_id: str
    answer: str
    sources: list[RetrievalSourceRecord] = Field(default_factory=list)
    memory_summary: str = ''
    namespace: str | None = None
    retrieval_count: int = 0
    confidence: float = 0.0
    latency_ms: int = 0
    used_llm: bool = False
    cache_hit: bool = False


class ChatHistoryResponseData(BaseModel):
    chat_id: str
    memory_summary: str = ''
    messages: list[dict[str, object]] = Field(default_factory=list)


class DocumentUploadResponseData(BaseModel):
    document_id: str
    chat_id: str
    filename: str
    status: str = 'uploaded'
    progress_stage: str = 'uploaded'
    stages: list[str] = Field(default_factory=lambda: ['uploaded', 'chunking', 'embedding', 'indexing', 'ready'])


class WorkspaceChatSummary(BaseModel):
    id: str
    user_id: str
    title: str
    pinned: bool = False
    memory_summary: str | None = None
    namespace: str | None = None
    is_demo: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    message_count: int = 0
    document_count: int = 0


class WorkspaceDocumentSummary(BaseModel):
    id: str
    chat_id: str
    user_id: str
    filename: str
    file_type: str
    file_size_bytes: int
    status: str
    pinecone_namespace: str
    chunk_count: int = 0
    error_message: str | None = None
    is_demo: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None


class WorkspaceBootstrapData(BaseModel):
    user: UserRecord
    chats: list[WorkspaceChatSummary] = Field(default_factory=list)
    metrics: dict[str, object] = Field(default_factory=dict)
    default_chat_id: str | None = None
    profile_menu: list[dict[str, object]] = Field(default_factory=list)


class WorkspaceChatDetailData(BaseModel):
    chat: WorkspaceChatSummary
    messages: list[dict[str, object]] = Field(default_factory=list)
    documents: list[WorkspaceDocumentSummary] = Field(default_factory=list)
