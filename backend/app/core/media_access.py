"""Short-lived, resource-scoped links for native video/document requests."""
from datetime import datetime, timedelta, timezone
from urllib.parse import quote

from app.core.security import create_access_token


def ticket_url(user, asset):
    token = create_access_token(
        user.id,
        extra_claims={"type": "media", "asset_id": str(asset.id), "exp": datetime.now(timezone.utc) + timedelta(minutes=5)},
        session_id=str(user._login_session.id), session_token=user._session_token,
    )
    return f"/api/v1/media/{asset.id}/content?ticket={quote(token, safe='')}"
