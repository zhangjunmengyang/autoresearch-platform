#!/usr/bin/env bash
set -euo pipefail

api_port="${1:-8010}"
web_port="${2:-5174}"
attempts="${DEV_WAIT_ATTEMPTS:-30}"
sleep_seconds="${DEV_WAIT_SLEEP:-0.5}"

for ((attempt = 1; attempt <= attempts; attempt += 1)); do
  api_ready=0
  web_ready=0

  if curl -fsS "http://127.0.0.1:${api_port}/api/v1/system/status" >/dev/null 2>&1; then
    api_ready=1
  fi
  if curl -fsS "http://127.0.0.1:${web_port}" >/dev/null 2>&1; then
    web_ready=1
  fi

  if [[ "${api_ready}" -eq 1 && "${web_ready}" -eq 1 ]]; then
    printf 'local stack ready: api=http://127.0.0.1:%s web=http://127.0.0.1:%s\n' "${api_port}" "${web_port}"
    exit 0
  fi

  sleep "${sleep_seconds}"
done

printf 'local stack unavailable after %s attempts\n' "${attempts}" >&2
printf 'API log: logs/api.log\n' >&2
printf 'Frontend log: logs/frontend.log\n' >&2
exit 1
