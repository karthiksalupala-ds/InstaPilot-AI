import uuid
from datetime import UTC, datetime, timedelta

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_workspace_role
from app.core.config import get_settings
from app.core.crypto import decrypt_token, encrypt_token
from app.db.session import get_db
from app.models.instagram import Agent, InstagramAccount, OAuthToken
from app.models.knowledge import KnowledgeBase
from app.models.tenant import WorkspaceMember
from app.schemas.instagram import (
    InstagramAccountResponse,
    InstagramAccountUpdateRequest,
    OAuthAuthorizeResponse,
)
from app.services.instagram_oauth import (
    REQUIRED_SCOPES,
    MetaInstagramOAuthClient,
    build_authorize_url,
    verify_oauth_state,
)

router = APIRouter(prefix="/instagram", tags=["instagram"])


def get_oauth_client() -> MetaInstagramOAuthClient:
    return MetaInstagramOAuthClient()


@router.get("/oauth/authorize", response_model=OAuthAuthorizeResponse)
async def oauth_authorize(
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin")),
) -> OAuthAuthorizeResponse:
    """Generate a Meta Instagram Login authorization URL for the active workspace."""
    settings = get_settings()
    if not settings.meta_app_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="META_APP_ID is not configured on the server",
        )
    url = build_authorize_url(caller.workspace_id, caller.user_id)
    return OAuthAuthorizeResponse(authorize_url=url)


@router.get("/oauth/callback")
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
    oauth_client: MetaInstagramOAuthClient = Depends(get_oauth_client),
) -> RedirectResponse:
    """Handle Meta OAuth callback, exchange for 60-day token, encrypt, and subscribe webhooks."""
    try:
        workspace_id, _user_id = verify_oauth_state(state)
    except (jwt.PyJWTError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OAuth state") from exc

    try:
        short_data = await oauth_client.exchange_code_for_short_token(code)
        short_token = str(short_data["access_token"])
        long_data = await oauth_client.exchange_short_for_long_token(short_token)
        long_token = str(long_data["access_token"])
        expires_in = int(long_data.get("expires_in", 5183944))
        profile = await oauth_client.fetch_profile(long_token)
    except (httpx.HTTPError, KeyError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Meta OAuth exchange failed: {exc}",
        ) from exc

    ig_user_id = str(profile["user_id"])
    ig_username = str(profile["username"])
    account_type = str(profile.get("account_type", "BUSINESS"))
    profile_pic = profile.get("profile_picture_url")

    now = datetime.now(UTC)
    expires_at = now + timedelta(seconds=expires_in)

    account = await db.scalar(
        select(InstagramAccount).where(InstagramAccount.ig_user_id == ig_user_id)
    )
    if account is not None and account.workspace_id != workspace_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This Instagram account is already connected to another workspace",
        )

    if account is None:
        account = InstagramAccount(
            workspace_id=workspace_id,
            ig_user_id=ig_user_id,
            ig_username=ig_username,
            account_type=account_type,
            profile_picture_url=profile_pic,
            connection_status="connected",
            automation_mode="manual",
            is_agent_enabled=False,
        )
        db.add(account)
        await db.flush()

        db.add(
            Agent(
                workspace_id=workspace_id,
                instagram_account_id=account.id,
                name=f"@{ig_username} Assistant",
                system_instructions=(
                    f"You are the official AI assistant for @{ig_username}. "
                    "Never invent prices, stock availability, or business policies."
                ),
                enabled_tools=[
                    "search_knowledge_base",
                    "search_products",
                    "get_product_details",
                    "create_lead",
                    "update_lead",
                    "get_customer_history",
                    "request_human_support",
                    "send_instagram_reply",
                ],
            )
        )
        db.add(
            KnowledgeBase(
                workspace_id=workspace_id,
                instagram_account_id=account.id,
                name=f"@{ig_username} Knowledge Base",
            )
        )
    else:
        account.ig_username = ig_username
        account.account_type = account_type
        account.profile_picture_url = profile_pic
        account.connection_status = "connected"

    token_row = await db.scalar(
        select(OAuthToken).where(OAuthToken.instagram_account_id == account.id)
    )
    encrypted = encrypt_token(long_token)
    if token_row is None:
        token_row = OAuthToken(
            workspace_id=workspace_id,
            instagram_account_id=account.id,
            encrypted_access_token=encrypted,
            token_type="long_lived",
            scopes=REQUIRED_SCOPES,
            issued_at=now,
            expires_at=expires_at,
        )
        db.add(token_row)
    else:
        token_row.encrypted_access_token = encrypted
        token_row.issued_at = now
        token_row.expires_at = expires_at
        token_row.last_refreshed_at = now

    try:
        await oauth_client.subscribe_webhooks(ig_user_id, long_token)
        account.webhook_subscribed = True
    except httpx.HTTPError:
        account.webhook_subscribed = False

    await db.commit()
    settings = get_settings()
    frontend_base = settings.cors_origin_list[0] if settings.cors_origin_list else "http://localhost:3000"
    return RedirectResponse(url=f"{frontend_base}/accounts?connected={ig_username}")


@router.get("/accounts", response_model=list[InstagramAccountResponse])
async def list_accounts(
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin", "operator", "viewer")),
    db: AsyncSession = Depends(get_db),
) -> list[InstagramAccountResponse]:
    """List connected Instagram accounts for the active workspace."""
    rows = (
        await db.execute(
            select(InstagramAccount, OAuthToken.expires_at)
            .outerjoin(OAuthToken, OAuthToken.instagram_account_id == InstagramAccount.id)
            .where(InstagramAccount.workspace_id == caller.workspace_id)
        )
    ).all()
    return [
        InstagramAccountResponse(
            id=acc.id,
            workspace_id=acc.workspace_id,
            ig_user_id=acc.ig_user_id,
            ig_username=acc.ig_username,
            account_type=acc.account_type,
            profile_picture_url=acc.profile_picture_url,
            connection_status=acc.connection_status,
            automation_mode=acc.automation_mode,
            is_agent_enabled=acc.is_agent_enabled,
            webhook_subscribed=acc.webhook_subscribed,
            last_webhook_at=acc.last_webhook_at,
            token_expires_at=expires_at,
        )
        for acc, expires_at in rows
    ]


@router.patch("/accounts/{account_id}", response_model=InstagramAccountResponse)
async def update_account(
    account_id: uuid.UUID,
    payload: InstagramAccountUpdateRequest,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
) -> InstagramAccountResponse:
    """Toggle agent ON/OFF or update default automation mode."""
    account = await db.scalar(
        select(InstagramAccount).where(
            InstagramAccount.id == account_id,
            InstagramAccount.workspace_id == caller.workspace_id,
        )
    )
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    if payload.is_agent_enabled is not None:
        account.is_agent_enabled = payload.is_agent_enabled
    if payload.automation_mode is not None:
        account.automation_mode = payload.automation_mode

    await db.commit()
    token_expires_at = await db.scalar(
        select(OAuthToken.expires_at).where(OAuthToken.instagram_account_id == account.id)
    )
    return InstagramAccountResponse(
        id=account.id,
        workspace_id=account.workspace_id,
        ig_user_id=account.ig_user_id,
        ig_username=account.ig_username,
        account_type=account.account_type,
        profile_picture_url=account.profile_picture_url,
        connection_status=account.connection_status,
        automation_mode=account.automation_mode,
        is_agent_enabled=account.is_agent_enabled,
        webhook_subscribed=account.webhook_subscribed,
        last_webhook_at=account.last_webhook_at,
        token_expires_at=token_expires_at,
    )


@router.post("/accounts/{account_id}/refresh-token", response_model=InstagramAccountResponse)
async def refresh_account_token(
    account_id: uuid.UUID,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
    oauth_client: MetaInstagramOAuthClient = Depends(get_oauth_client),
) -> InstagramAccountResponse:
    """Refresh a long-lived token (enforcing Meta's >=24h old and unexpired rules)."""
    row = (
        await db.execute(
            select(InstagramAccount, OAuthToken)
            .join(OAuthToken, OAuthToken.instagram_account_id == InstagramAccount.id)
            .where(
                InstagramAccount.id == account_id,
                InstagramAccount.workspace_id == caller.workspace_id,
            )
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account or token not found")

    account, token_row = row
    now = datetime.now(UTC)
    if token_row.expires_at <= now:
        account.connection_status = "error"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token has already expired; manual Instagram OAuth reconnection is required",
        )
    if now - token_row.issued_at < timedelta(hours=24):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Meta requires tokens to be at least 24 hours old before refreshing",
        )

    refreshed = await oauth_client.refresh_long_lived_token(
        decrypt_token(token_row.encrypted_access_token)
    )
    new_token = str(refreshed["access_token"])
    expires_in = int(refreshed.get("expires_in", 5183944))

    token_row.encrypted_access_token = encrypt_token(new_token)
    token_row.issued_at = now
    token_row.expires_at = now + timedelta(seconds=expires_in)
    token_row.last_refreshed_at = now
    account.connection_status = "connected"
    await db.commit()

    return InstagramAccountResponse(
        id=account.id,
        workspace_id=account.workspace_id,
        ig_user_id=account.ig_user_id,
        ig_username=account.ig_username,
        account_type=account.account_type,
        profile_picture_url=account.profile_picture_url,
        connection_status=account.connection_status,
        automation_mode=account.automation_mode,
        is_agent_enabled=account.is_agent_enabled,
        webhook_subscribed=account.webhook_subscribed,
        last_webhook_at=account.last_webhook_at,
        token_expires_at=token_row.expires_at,
    )


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_account(
    account_id: uuid.UUID,
    caller: WorkspaceMember = Depends(require_workspace_role("owner", "admin")),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Disconnect an Instagram account and purge its encrypted OAuth tokens and scoped data."""
    account = await db.scalar(
        select(InstagramAccount).where(
            InstagramAccount.id == account_id,
            InstagramAccount.workspace_id == caller.workspace_id,
        )
    )
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")

    await db.delete(account)
    await db.commit()
