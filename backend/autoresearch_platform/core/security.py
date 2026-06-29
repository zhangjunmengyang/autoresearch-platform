"""Optional API token security and request audit helpers."""

from __future__ import annotations

from dataclasses import dataclass
from hmac import compare_digest
from typing import Any

from fastapi import Request


WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


@dataclass(frozen=True)
class RequestAuth:
    allowed: bool
    auth_required: bool
    outcome: str
    reason: str = ""


def public_paths(api_prefix: str) -> set[str]:
    return {
        "/",
        "/docs",
        "/redoc",
        f"{api_prefix}/openapi.json",
        f"{api_prefix}/agent/onboarding",
        f"{api_prefix}/method-loop",
        f"{api_prefix}/capabilities",
        f"{api_prefix}/system/status",
        f"{api_prefix}/system/readiness",
        f"{api_prefix}/system/security",
    }


def security_status(api_prefix: str, api_token: str | None) -> dict[str, Any]:
    return {
        "auth_required": bool(api_token),
        "auth_scheme": "bearer" if api_token else "disabled_for_local_development",
        "protected_scope": "all_non_public_api_endpoints",
        "public_endpoints": sorted(public_paths(api_prefix)),
        "audit": {
            "writes": True,
            "denied_requests": True,
            "body_storage": False,
            "collection": "logs",
        },
        "safety": "deployment_security_metadata_no_secret_echo",
    }


def authorize_request(request: Request, *, api_prefix: str, api_token: str | None) -> RequestAuth:
    path = request.url.path
    if request.method == "OPTIONS":
        return RequestAuth(True, bool(api_token), "cors_preflight")
    if not path.startswith(api_prefix):
        return RequestAuth(True, bool(api_token), "outside_api")
    if path in public_paths(api_prefix):
        return RequestAuth(True, bool(api_token), "public")
    if not api_token:
        return RequestAuth(True, False, "disabled")

    expected = f"Bearer {api_token}"
    provided = request.headers.get("authorization", "")
    if compare_digest(provided, expected):
        return RequestAuth(True, True, "passed")
    return RequestAuth(False, True, "failed", "missing_or_invalid_bearer_token")


def should_audit_request(request: Request, auth: RequestAuth) -> bool:
    if request.method in WRITE_METHODS:
        return True
    return auth.auth_required and not auth.allowed
