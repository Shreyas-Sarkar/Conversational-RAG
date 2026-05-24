from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(ROOT_DIR / 'backend' / '.env',),
        env_file_encoding='utf-8',
        extra='ignore'
    )

    supabase_url: str = ''
    supabase_anon_key: str = ''
    supabase_service_role_key: str = ''
    pinecone_api_key: str = ''
    pinecone_index_name: str = ''
    pinecone_cloud: str = 'aws'
    pinecone_region: str = 'us-east-1'
    groq_api_key: str = ''
    groq_model_name: str = 'llama-3.3-70b-versatile'
    groq_temperature: float = 0.2
    groq_top_p: float = 0.9
    frontend_url: str = 'http://localhost:3000'


settings = Settings()
