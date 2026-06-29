#!/usr/bin/env python3
"""Validate AutoResearch external Agent onboarding through read-only REST calls."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any


REQUIRED_OPERATION_METADATA = [
    "x-agent-guidance",
    "x-capability-group",
    "x-safety-level",
    "x-agent-visible",
    "x-response-contract",
]
HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
EXPECTED_ONBOARDING_SCHEMA = "autoresearch.agent_onboarding.v1"
EXPECTED_ONBOARDING_SAFETY = "read_only_onboarding_no_execution_no_external_access"
EXPECTED_REPORT_SAFETY = "read_only_validation_no_execution"


def normalize_base_url(value: str) -> str:
    base_url = value.rstrip("/")
    if base_url.endswith("/api/v1"):
        return base_url
    return f"{base_url}/api/v1"


def _check(check_id: str, status: str, message: str, details: dict[str, Any] | None = None) -> dict[str, Any]:
    check = {"id": check_id, "status": status, "message": message}
    if details:
        check["details"] = details
    return check


def _missing_keys(payload: dict[str, Any], keys: list[str]) -> list[str]:
    return [key for key in keys if key not in payload]


def _operation_metadata_gaps(openapi: dict[str, Any]) -> tuple[list[dict[str, str]], int]:
    missing: list[dict[str, str]] = []
    operation_count = 0
    for path, methods in openapi.get("paths", {}).items():
        if not isinstance(methods, dict):
            continue
        for method, operation in methods.items():
            if method not in HTTP_METHODS:
                continue
            operation_count += 1
            if not isinstance(operation, dict):
                for key in REQUIRED_OPERATION_METADATA:
                    missing.append({"method": method.upper(), "path": path, "key": key})
                continue
            for key in REQUIRED_OPERATION_METADATA:
                if key not in operation:
                    missing.append({"method": method.upper(), "path": path, "key": key})
    return missing, operation_count


def build_validation_report(
    *,
    base_url: str,
    onboarding: dict[str, Any],
    openapi: dict[str, Any],
    token_env: str = "AUTORESEARCH_API_TOKEN",
    token_present: bool = False,
) -> dict[str, Any]:
    normalized_base_url = normalize_base_url(base_url)
    checks: list[dict[str, Any]] = []

    onboarding_required = [
        "schema",
        "state",
        "openapi",
        "skill",
        "security",
        "readiness",
        "recommended_first_calls",
        "integrity",
        "safety",
    ]
    missing_onboarding = _missing_keys(onboarding, onboarding_required)
    schema_ok = (
        not missing_onboarding
        and onboarding.get("schema") == EXPECTED_ONBOARDING_SCHEMA
        and onboarding.get("openapi") == "/api/v1/openapi.json"
    )
    checks.append(
        _check(
            "onboarding_schema",
            "pass" if schema_ok else "fail",
            "onboarding bundle uses the expected schema and OpenAPI pointer"
            if schema_ok
            else "onboarding bundle schema or OpenAPI pointer is invalid",
            {
                "missing": missing_onboarding,
                "schema": onboarding.get("schema"),
                "openapi": onboarding.get("openapi"),
            }
            if not schema_ok
            else None,
        )
    )

    onboarding_state = onboarding.get("state")
    state_ok = onboarding_state in {"ready", "degraded"}
    checks.append(
        _check(
            "onboarding_state",
            "pass" if state_ok else "fail",
            "platform state is usable for read-only Agent onboarding"
            if state_ok
            else "platform state is blocked or unknown",
            {"state": onboarding_state} if not state_ok else None,
        )
    )

    integrity = onboarding.get("integrity", {})
    integrity_violations = [
        key
        for key in ["external_reads", "external_writes", "executes_runtime"]
        if integrity.get(key) is not False
    ]
    safety_ok = onboarding.get("safety") == EXPECTED_ONBOARDING_SAFETY
    read_only_ok = safety_ok and not integrity_violations
    checks.append(
        _check(
            "onboarding_read_only_integrity",
            "pass" if read_only_ok else "fail",
            "onboarding is metadata-only and does not claim Runtime access"
            if read_only_ok
            else "onboarding violates the platform read-only boundary",
            {
                "safety": onboarding.get("safety"),
                "violations": integrity_violations,
            }
            if not read_only_ok
            else None,
        )
    )

    skill = onboarding.get("skill", {})
    load_order = skill.get("load_order", []) if isinstance(skill, dict) else []
    required_refs = ["references/bootstrap.md", "references/safety-boundaries.md"]
    missing_refs = [ref for ref in required_refs if ref not in load_order]
    skill_ok = isinstance(skill, dict) and skill.get("name") == "auto-research" and not missing_refs
    checks.append(
        _check(
            "skill_load_order",
            "pass" if skill_ok else "fail",
            "auto-research Skill exposes the minimum progressive references"
            if skill_ok
            else "auto-research Skill loading order is incomplete",
            {"skill_name": skill.get("name") if isinstance(skill, dict) else None, "missing": missing_refs}
            if not skill_ok
            else None,
        )
    )

    first_calls = onboarding.get("recommended_first_calls", [])
    required_calls = [
        "GET /api/v1/agent/onboarding",
        "GET /api/v1/system/security",
        "GET /api/v1/system/readiness",
        "GET /api/v1/research/design/audit",
    ]
    missing_calls = [call for call in required_calls if call not in first_calls]
    calls_ok = not missing_calls
    checks.append(
        _check(
            "recommended_first_calls",
            "pass" if calls_ok else "fail",
            "onboarding recommends the minimum safe first calls"
            if calls_ok
            else "onboarding first-call list is incomplete",
            {"missing": missing_calls} if not calls_ok else None,
        )
    )

    entrypoint = openapi.get("x-agent-entrypoint", {})
    onboarding_path_exists = "/api/v1/agent/onboarding" in openapi.get("paths", {})
    capabilities = openapi.get("x-agent-capabilities", [])
    entrypoint_ok = (
        isinstance(entrypoint, dict)
        and entrypoint.get("openapi") == "/api/v1/openapi.json"
        and onboarding_path_exists
        and isinstance(capabilities, list)
        and len(capabilities) > 0
    )
    checks.append(
        _check(
            "openapi_entrypoint",
            "pass" if entrypoint_ok else "fail",
            "OpenAPI advertises the Agent entrypoint and capability catalog"
            if entrypoint_ok
            else "OpenAPI entrypoint metadata is incomplete",
            {
                "entrypoint_openapi": entrypoint.get("openapi") if isinstance(entrypoint, dict) else None,
                "has_onboarding_path": onboarding_path_exists,
                "capability_count": len(capabilities) if isinstance(capabilities, list) else 0,
            }
            if not entrypoint_ok
            else None,
        )
    )

    missing_metadata, operation_count = _operation_metadata_gaps(openapi)
    metadata_ok = not missing_metadata and operation_count > 0
    checks.append(
        _check(
            "openapi_agent_metadata",
            "pass" if metadata_ok else "fail",
            "all public operations expose Agent-facing metadata"
            if metadata_ok
            else "some public operations are missing Agent-facing metadata",
            {"missing": missing_metadata, "operation_count": operation_count}
            if not metadata_ok
            else {"operation_count": operation_count},
        )
    )

    failed = [check for check in checks if check["status"] == "fail"]
    return {
        "schema": "autoresearch.agent_onboarding_validation.v1",
        "status": "fail" if failed else "pass",
        "base_url": normalized_base_url,
        "onboarding_state": onboarding_state,
        "openapi_operation_count": operation_count,
        "checks": checks,
        "token_env": token_env,
        "token_present": token_present,
        "safety": EXPECTED_REPORT_SAFETY,
    }


def exit_code_for_report(report: dict[str, Any]) -> int:
    return 0 if report.get("status") == "pass" else 2


def fetch_json(base_url: str, path: str, *, token: str | None, timeout: float) -> dict[str, Any]:
    url = f"{normalize_base_url(base_url)}/{path.lstrip('/')}"
    headers = {"Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if isinstance(payload, dict) and "data" in payload and isinstance(payload["data"], dict):
        return payload["data"]
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"{path} did not return a JSON object")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate AutoResearch Agent onboarding through read-only REST endpoints."
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8010/api/v1",
        help="API base URL. Values without /api/v1 are normalized to include it.",
    )
    parser.add_argument(
        "--token-env",
        default="AUTORESEARCH_API_TOKEN",
        help="Environment variable containing the optional Bearer token.",
    )
    parser.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout in seconds.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    token = os.environ.get(args.token_env) if args.token_env else None
    base_url = normalize_base_url(args.base_url)
    try:
        onboarding = fetch_json(base_url, "/agent/onboarding", token=token, timeout=args.timeout)
        openapi = fetch_json(base_url, "/openapi.json", token=token, timeout=args.timeout)
        report = build_validation_report(
            base_url=base_url,
            onboarding=onboarding,
            openapi=openapi,
            token_env=args.token_env,
            token_present=bool(token),
        )
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, ValueError, json.JSONDecodeError) as exc:
        report = {
            "schema": "autoresearch.agent_onboarding_validation.v1",
            "status": "fail",
            "base_url": base_url,
            "checks": [
                {
                    "id": "read_only_http_fetch",
                    "status": "fail",
                    "message": "could not fetch onboarding or OpenAPI JSON through read-only REST",
                    "details": {"error_type": exc.__class__.__name__, "error": str(exc)},
                }
            ],
            "token_env": args.token_env,
            "token_present": bool(token),
            "safety": EXPECTED_REPORT_SAFETY,
        }
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return exit_code_for_report(report)


if __name__ == "__main__":
    sys.exit(main())
