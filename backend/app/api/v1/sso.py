"""SSO authentication routes (Phase 8 - reserved).

These endpoints are stubs for enterprise WeChat SSO integration.
The SSOProvider implements the same AuthenticationProvider interface
as LocalAuthProvider, so business code requires zero changes.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.auth.sso import SSOProvider

router = APIRouter(prefix="/auth/sso", tags=["sso"])


class SSOCallbackRequest(BaseModel):
    code: str
    state: str | None = None


@router.get("/login")
def sso_login(redirect_uri: str = ""):
    """Initiate SSO login flow. Returns authorization URL.

    Phase 8: will redirect to enterprise WeChat OIDC authorization endpoint.
    """
    return {
        "status": "not_implemented",
        "message": "SSO login will be available in Phase 8",
        "provider": "wecom",
        "redirect_uri": redirect_uri,
    }


@router.post("/callback")
def sso_callback(body: SSOCallbackRequest):
    """Handle SSO callback with authorization code.

    Phase 8: will exchange code for access token, fetch user info,
    auto-provision user if first login, and return JWT tokens.
    """
    return {
        "status": "not_implemented",
        "message": "SSO callback will be available in Phase 8",
    }


@router.get("/logout")
def sso_logout():
    """SSO logout - clears local session and redirects to IdP logout.

    Phase 8: will call enterprise WeChat logout endpoint.
    """
    return {
        "status": "not_implemented",
        "message": "SSO logout will be available in Phase 8",
    }
