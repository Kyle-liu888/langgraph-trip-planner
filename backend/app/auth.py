"""Supabase JWT authentication using cached public signing keys, never user IDs from input."""
import asyncio
from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings


@dataclass(frozen=True)
class User:
    id: str
    expires_at: int


bearer = HTTPBearer(auto_error=False)


@lru_cache(maxsize=8)
def jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url, cache_jwk_set=True, lifespan=300, timeout=10)


def verify_token(token: str, url: str, audience: str) -> User:
    issuer = url.rstrip("/") + "/auth/v1"
    key = jwks_client(issuer + "/.well-known/jwks.json").get_signing_key_from_jwt(token)
    claims = jwt.decode(token, key.key, algorithms=["RS256", "ES256"],
                        issuer=issuer, audience=audience,
                        options={"require": ["sub", "exp", "iss", "aud"]})
    if claims.get("role") != "authenticated" or claims.get("is_anonymous"):
        raise jwt.InvalidTokenError("Registered user required")
    return User(str(UUID(claims["sub"])), int(claims["exp"]))


async def require_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> User:
    if not credentials:
        raise HTTPException(401, {"code": "UNAUTHENTICATED", "message": "请先登录"})
    settings = get_settings()
    if not settings.supabase_url:
        raise HTTPException(503, {"code": "AUTH_NOT_CONFIGURED", "message": "请先配置 Supabase 项目地址"})
    try:
        return await asyncio.to_thread(verify_token, credentials.credentials,
                                       settings.supabase_url, settings.supabase_jwt_audience)
    except jwt.PyJWKClientConnectionError:
        raise HTTPException(503, {"code": "AUTH_UNAVAILABLE", "message": "暂时无法连接登录服务，请稍后重试"}) from None
    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise HTTPException(401, {"code": "INVALID_SESSION", "message": "登录已失效，请重新登录"}) from None
