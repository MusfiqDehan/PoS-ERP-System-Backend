from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone
from django_tenants.utils import get_public_schema_name, schema_context
from rest_framework_simplejwt.tokens import RefreshToken

from apps.tenancy.models import PlatformUserRole, User as TenancyUser
from apps.tenancy.services.auth import AuthService

User = get_user_model()


@dataclass
class PlatformAuthTokens:
    access: str
    refresh: str
    user: TenancyUser


class PlatformAuthService:
    MAX_FAILED_ATTEMPTS = 5
    LOCKOUT_SECONDS = 15 * 60

    @staticmethod
    def _issue_tokens(user: TenancyUser) -> tuple[str, str]:
        refresh = RefreshToken.for_user(user)
        refresh["platform_user"] = True
        access = refresh.access_token
        access["platform_user"] = True
        return str(access), str(refresh)

    @classmethod
    def login(cls, *, email: str, password: str) -> PlatformAuthTokens:
        email = email.strip().lower()
        cache_key = f"platform_auth:{email}"
        failed_attempts = int(cache.get(cache_key, 0))
        if failed_attempts >= cls.MAX_FAILED_ATTEMPTS:
            raise PermissionError("Too many failed attempts. Try later.")

        with schema_context(get_public_schema_name()):
            user = User.objects.filter(email__iexact=email, tenant__isnull=True).first()
            if user is None or not user.check_password(password):
                cache.set(
                    cache_key, failed_attempts + 1, timeout=cls.LOCKOUT_SECONDS
                )
                raise ValueError("Invalid credentials.")
            if user.password_set_at is None:
                cache.set(
                    cache_key, failed_attempts + 1, timeout=cls.LOCKOUT_SECONDS
                )
                raise ValueError("Invalid credentials.")
            if not user.is_active or user.is_deleted:
                raise PermissionError("User account is inactive.")
            if not PlatformUserRole.objects.filter(user=user).exists():
                raise PermissionError("Platform access denied.")

            user.last_login = timezone.now()
            user.save(update_fields=["last_login"])
            access, refresh = cls._issue_tokens(user)

        cache.delete(cache_key)
        return PlatformAuthTokens(access=access, refresh=refresh, user=user)

    @staticmethod
    def refresh(refresh_token: str) -> dict[str, str]:
        refresh = RefreshToken(refresh_token)  # type: ignore[arg-type]
        if not refresh.get("platform_user"):
            raise ValueError("Invalid or expired refresh token.")
        access = refresh.access_token
        access["platform_user"] = True
        return {"access": str(access), "refresh": str(refresh)}

    @staticmethod
    def serialize_user(user: TenancyUser) -> dict[str, Any]:
        return AuthService.serialize_user(user)

    @classmethod
    def tokens_for_user(cls, user: TenancyUser) -> dict[str, str]:
        access, refresh = cls._issue_tokens(user)
        return {"access": access, "refresh": refresh}
