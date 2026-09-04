"""Local opaque sessions, origin checking and synchronizer CSRF protection."""
import hashlib
import hmac
import time
from dataclasses import dataclass
from datetime import timezone

from fastapi import HTTPException, Request

from .config import get_settings
from .database import Account, LoginSession

SESSION_COOKIE = "trip_session"
CSRF_COOKIE = "trip_login_csrf"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@dataclass(frozen=True)
class User:
    id: str
    expires_at: int
    email: str = ""
    session_hash: str = ""


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def csrf_for(token: str) -> str:
    return hmac.new(token.encode(), b"trip-csrf-v1", hashlib.sha256).hexdigest()


def sessions_for(request: Request):
    sessions = getattr(request.app.state, "auth_sessions", None)
    if sessions is None:
        raise HTTPException(503, {"code": "STORAGE_NOT_READY", "message": "本地数据库尚未就绪，请检查数据库迁移和后端日志"})
    return sessions


def check_origin(request: Request):
    if request.headers.get("origin") not in get_settings().get_cors_origins_list():
        raise HTTPException(403, {"code": "UNTRUSTED_ORIGIN", "message": "请求来源未被允许，请从本地前端访问"})


def check_csrf(request: Request, expected: str):
    check_origin(request)
    supplied = request.headers.get("x-csrf-token", "")
    if not expected or not supplied.isascii() or not hmac.compare_digest(supplied, expected):
        raise HTTPException(403, {"code": "CSRF_FAILED", "message": "页面安全凭据已失效，请刷新后重试"})


async def lookup_user(request: Request) -> User | None:
    token = request.cookies.get(SESSION_COOKIE, "")
    if not token or len(token) > 256:
        return None
    async with sessions_for(request)() as db:
        session = await db.get(LoginSession, digest(token))
        if not session:
            return None
        expires = int(session.expires_at.replace(tzinfo=timezone.utc).timestamp())
        account = await db.get(Account, session.user_id) if expires > time.time() else None
        if account:
            return User(account.id, expires, account.email, session.token_hash)
    return None


async def require_user(request: Request) -> User:
    user = await lookup_user(request)
    if user is None:
        raise HTTPException(401, {"code": "UNAUTHENTICATED", "message": "请先登录或重新登录"})
    if request.method not in SAFE_METHODS:
        check_csrf(request, csrf_for(request.cookies[SESSION_COOKIE]))
    return user


async def session_alive(request: Request, user: User) -> bool:
    """Recheck durable revocation before emitting each SSE batch."""
    if time.time() >= user.expires_at or not user.session_hash:
        return False
    current = await lookup_user(request)
    return current is not None and current.session_hash == user.session_hash
