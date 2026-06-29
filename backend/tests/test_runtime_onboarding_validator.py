from __future__ import annotations

import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "validate_agent_onboarding.py"


def load_validator():
    assert SCRIPT_PATH.exists(), "scripts/validate_agent_onboarding.py is missing"
    spec = importlib.util.spec_from_file_location("validate_agent_onboarding", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sample_onboarding() -> dict:
    return {
        "schema": "autoresearch.agent_onboarding.v1",
        "state": "degraded",
        "openapi": "/api/v1/openapi.json",
        "docs": ["docs/architecture/reference.md"],
        "skill": {
            "name": "auto-research",
            "load_order": [
                "references/bootstrap.md",
                "references/research-design.md",
                "references/execution-ledger.md",
                "references/safety-boundaries.md",
            ],
        },
        "security": {"auth_required": False, "auth_scheme": "optional_bearer_token"},
        "readiness": {"state": "degraded"},
        "capability_count": 2,
        "capability_groups": {
            "platform_readiness": {"primary_endpoint": "GET /api/v1/agent/onboarding"},
            "research_methodology": {"primary_endpoint": "GET /api/v1/research/design/audit"},
        },
        "recommended_first_calls": [
            "GET /api/v1/agent/onboarding",
            "GET /api/v1/system/security",
            "GET /api/v1/system/readiness",
            "GET /api/v1/research/design/audit",
        ],
        "recommended_next_actions": [],
        "integrity": {
            "external_reads": False,
            "external_writes": False,
            "executes_runtime": False,
        },
        "safety": "read_only_onboarding_no_execution_no_external_access",
    }


def sample_openapi() -> dict:
    metadata = {
        "x-agent-guidance": {"purpose": "read-only onboarding"},
        "x-capability-group": "platform_readiness",
        "x-safety-level": "read",
        "x-agent-visible": True,
        "x-response-contract": "JSON response model documented in OpenAPI",
    }
    return {
        "openapi": "3.1.0",
        "x-agent-entrypoint": {"openapi": "/api/v1/openapi.json", "base_path": "/api/v1"},
        "x-agent-capabilities": [
            {"id": "platform_readiness", "primary_endpoint": "GET /api/v1/agent/onboarding"}
        ],
        "paths": {
            "/api/v1/agent/onboarding": {"get": dict(metadata)},
            "/api/v1/system/security": {"get": {**metadata, "x-capability-group": "system"}},
        },
    }


def test_validator_accepts_degraded_read_only_onboarding_bundle():
    validator = load_validator()

    report = validator.build_validation_report(
        base_url="http://127.0.0.1:8010/api/v1",
        onboarding=sample_onboarding(),
        openapi=sample_openapi(),
        token_env="AUTORESEARCH_API_TOKEN",
        token_present=True,
    )

    assert report["status"] == "pass"
    assert report["onboarding_state"] == "degraded"
    assert report["safety"] == "read_only_validation_no_execution"
    assert report["token_env"] == "AUTORESEARCH_API_TOKEN"
    assert report["token_present"] is True
    assert "secret" not in json.dumps(report, ensure_ascii=False)
    assert {check["id"]: check["status"] for check in report["checks"]} == {
        "onboarding_schema": "pass",
        "onboarding_state": "pass",
        "onboarding_read_only_integrity": "pass",
        "skill_load_order": "pass",
        "recommended_first_calls": "pass",
        "openapi_entrypoint": "pass",
        "openapi_agent_metadata": "pass",
    }
    assert validator.exit_code_for_report(report) == 0


def test_validator_fails_when_onboarding_claims_runtime_access():
    validator = load_validator()
    onboarding = sample_onboarding()
    onboarding["integrity"]["external_reads"] = True

    report = validator.build_validation_report(
        base_url="http://127.0.0.1:8010/api/v1",
        onboarding=onboarding,
        openapi=sample_openapi(),
    )

    assert report["status"] == "fail"
    integrity_check = next(
        check for check in report["checks"] if check["id"] == "onboarding_read_only_integrity"
    )
    assert integrity_check["status"] == "fail"
    assert "external_reads" in json.dumps(integrity_check, ensure_ascii=False)
    assert validator.exit_code_for_report(report) == 2


def test_validator_fails_when_openapi_operation_lacks_agent_metadata():
    validator = load_validator()
    openapi = sample_openapi()
    del openapi["paths"]["/api/v1/system/security"]["get"]["x-response-contract"]

    report = validator.build_validation_report(
        base_url="http://127.0.0.1:8010/api/v1",
        onboarding=sample_onboarding(),
        openapi=openapi,
    )

    assert report["status"] == "fail"
    metadata_check = next(check for check in report["checks"] if check["id"] == "openapi_agent_metadata")
    assert metadata_check["status"] == "fail"
    assert {
        "method": "GET",
        "path": "/api/v1/system/security",
        "key": "x-response-contract",
    } in metadata_check["details"]["missing"]


def test_validator_normalizes_api_base_url_without_hiding_api_prefix():
    validator = load_validator()

    assert validator.normalize_base_url("http://127.0.0.1:8010") == "http://127.0.0.1:8010/api/v1"
    assert validator.normalize_base_url("http://127.0.0.1:8010/") == "http://127.0.0.1:8010/api/v1"
    assert validator.normalize_base_url("http://127.0.0.1:8010/api/v1/") == "http://127.0.0.1:8010/api/v1"
