from supabase import AsyncClient, AsyncClientOptions, create_async_client

from app.config import settings


async def create_user_client(access_token: str) -> AsyncClient:
    """Create a Supabase client that enforces RLS as the authenticated user."""
    options = AsyncClientOptions(
        headers={"Authorization": f"Bearer {access_token}"},
        auto_refresh_token=False,
        persist_session=False,
    )
    return await create_async_client(
        str(settings.supabase_url),
        settings.supabase_anon_key.get_secret_value(),
        options,
    )


async def create_service_role_client() -> AsyncClient:
    """Create a privileged backend-only Supabase client that bypasses RLS."""
    service_role_key = settings.supabase_service_role_key.get_secret_value()
    options = AsyncClientOptions(
        headers={"Authorization": f"Bearer {service_role_key}"},
        auto_refresh_token=False,
        persist_session=False,
    )
    return await create_async_client(
        str(settings.supabase_url),
        service_role_key,
        options,
    )
