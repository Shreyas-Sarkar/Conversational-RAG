from app.core.config import settings


def get_supabase_client_config() -> dict[str, str]:
    return {
        'supabase_url': settings.supabase_url,
        'supabase_service_role_key': settings.supabase_service_role_key
    }
