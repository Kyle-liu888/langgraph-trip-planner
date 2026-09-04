"""Local registration/login; no email verification or external identity service."""
import asyncio
import secrets
import time
from datetime import timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from ...auth import (CSRF_COOKIE, SESSION_COOKIE, User, check_csrf, csrf_for,
                     digest, lookup_user, require_user, sessions_for)
from ...config import get_settings
from ...database import Account, AuthAttempt, LoginSession, now

router = APIRouter(prefix="/auth", tags=["本地账号"])
hasher = PasswordHasher()
dummy_hash = hasher.hash(secrets.token_urlsafe(32))
auth_lock = asyncio.Lock()  # Single app process enforced by PostgreSQL advisory lock.
SESSION_SECONDS = 7 * 24 * 3600


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def email_identifier(cls, value: str):
        value = value.strip().lower()
        if value.count("@") != 1 or any(c.isspace() or ord(c) < 32 for c in value):
            raise ValueError("invalid email identifier")
        local, domain = value.split("@")
        if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise ValueError("invalid email identifier")
        return value


def cookie(response: Response, name: str, value: str, max_age: int):
    response.set_cookie(name, value, max_age=max_age, httponly=True, samesite="strict",
                        secure=get_settings().session_cookie_secure, path="/api")
    response.headers["Cache-Control"] = "no-store"


def payload(account: Account | User, token: str):
    return {"user": {"id": account.id, "email": account.email, "email_verified": False},
            "csrf_token": csrf_for(token)}


async def limit_attempts(request: Request, email: str):
    """Persist fixed-window limits. Do not trust forwarded IP headers."""
    bucket = int(time.time()) // 900
    host = request.client.host if request.client else "unknown"
    async with sessions_for(request)() as db:
        await db.execute(delete(AuthAttempt).where(AuthAttempt.expires_at < now()))
        blocked = False
        for scope, value, limit in (("ip", host, 60), ("email", email, 10)):
            key = digest(f"{scope}:{value}:{bucket}")
            row = await db.get(AuthAttempt, key)
            if row is None:
                row = AuthAttempt(key=key, count=0, expires_at=now() + timedelta(minutes=30))
                db.add(row)
            row.count += 1
            blocked |= row.count > limit
        await db.commit()
    if blocked:
        raise HTTPException(429, {"code": "AUTH_RATE_LIMIT", "message": "尝试过于频繁，请 15 分钟后重试"},
                            headers={"Retry-After": "900"})


@router.get("/session")
async def current_session(request: Request, response: Response):
    sessions_for(request)
    response.headers["Cache-Control"] = "no-store"
    if user := await lookup_user(request):
        return payload(user, request.cookies[SESSION_COOKIE])
    token = request.cookies.get(CSRF_COOKIE, "")
    if len(token) != 43:
        token = secrets.token_urlsafe(32)
    cookie(response, CSRF_COOKIE, token, 3600)
    return {"user": None, "csrf_token": token}


async def authenticate(body: Credentials, request: Request, response: Response, *, register: bool):
    existing = await lookup_user(request)
    expected = csrf_for(request.cookies[SESSION_COOKIE]) if existing else request.cookies.get(CSRF_COOKIE, "")
    check_csrf(request, expected)
    async with auth_lock:
        await limit_attempts(request, body.email)
        async with sessions_for(request)() as db:
            account = await db.scalar(select(Account).where(Account.email == body.email))
            if register:
                hashed = await asyncio.to_thread(hasher.hash, body.password)
                if account:
                    raise HTTPException(400, {"code": "REGISTRATION_FAILED", "message": "无法注册，请检查信息或尝试登录"})
                account = Account(email=body.email, password_hash=hashed)
                db.add(account)
                try:
                    await db.flush()
                except IntegrityError:
                    await db.rollback()
                    raise HTTPException(400, {"code": "REGISTRATION_FAILED", "message": "无法注册，请检查信息或尝试登录"}) from None
            else:
                try:
                    valid = await asyncio.to_thread(hasher.verify, account.password_hash if account else dummy_hash, body.password)
                except (VerificationError, InvalidHashError):
                    valid = False
                if not valid or account is None:
                    raise HTTPException(401, {"code": "LOGIN_FAILED", "message": "邮箱或密码不正确"})
                if hasher.check_needs_rehash(account.password_hash):
                    account.password_hash = await asyncio.to_thread(hasher.hash, body.password)
            await db.execute(delete(LoginSession).where(LoginSession.expires_at < now()))
            if old := request.cookies.get(SESSION_COOKIE):
                await db.execute(delete(LoginSession).where(LoginSession.token_hash == digest(old)))
            token = secrets.token_urlsafe(32)
            db.add(LoginSession(token_hash=digest(token), user_id=account.id,
                                expires_at=now() + timedelta(seconds=SESSION_SECONDS)))
            await db.commit()
            result = payload(account, token)
    cookie(response, SESSION_COOKIE, token, SESSION_SECONDS)
    response.delete_cookie(CSRF_COOKIE, path="/api")
    return result


@router.post("/register", status_code=201)
async def register(body: Credentials, request: Request, response: Response):
    return await authenticate(body, request, response, register=True)


@router.post("/login")
async def login(body: Credentials, request: Request, response: Response):
    return await authenticate(body, request, response, register=False)


@router.post("/logout", status_code=204)
async def logout(request: Request, response: Response, user: User = Depends(require_user)):
    async with sessions_for(request)() as db:
        await db.execute(delete(LoginSession).where(LoginSession.token_hash == user.session_hash))
        await db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/api")
    response.headers["Cache-Control"] = "no-store"
    if runs := getattr(request.app.state, "run_manager", None):
        for signal in runs.changed.values():
            signal.set()
