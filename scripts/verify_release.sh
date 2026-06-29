#!/usr/bin/env bash
set -euo pipefail

make test
cd frontend && npm run typecheck
cd ..
make openapi

python - <<'PY'
import json
from pathlib import Path

schema = json.loads(Path("docs/openapi.json").read_text())
missing = []
for path, methods in schema["paths"].items():
    for method, operation in methods.items():
        if method not in {"get", "post", "patch", "put", "delete"}:
            continue
        for key in [
            "x-agent-guidance",
            "x-capability-group",
            "x-safety-level",
            "x-agent-visible",
            "x-response-contract",
        ]:
            if key not in operation:
                missing.append((method, path, key))
if missing:
    raise SystemExit(f"missing agent metadata: {missing}")

text = json.dumps(schema, ensure_ascii=False).lower()
allowed_groups = {
    "artifact_registry",
    "benchmark_registry",
    "capabilities",
    "decision_records",
    "evidence_records",
    "experience_curation",
    "platform_readiness",
    "research_audit",
    "research_intake",
    "research_methodology",
    "research_round_ledger",
    "research_session_ledger",
    "review_events",
    "runtime_event_ledger",
    "source_to_insight",
    "system",
}
unknown_groups = set()
for capability in schema.get("x-agent-capabilities", []):
    group = capability.get("id")
    if group not in allowed_groups:
        unknown_groups.add(group)
for path, methods in schema["paths"].items():
    for method, operation in methods.items():
        if method not in {"get", "post", "patch", "put", "delete"}:
            continue
        group = operation.get("x-capability-group")
        if group not in allowed_groups:
            unknown_groups.add(group)
if unknown_groups:
    raise SystemExit(f"unknown capability groups leaked into public contract: {sorted(unknown_groups)}")
PY
