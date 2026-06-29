#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PATH="${HOME}/.local/bin:${PATH}"

mode="${1:-}"
if [[ "${mode}" == "--deps-only" ]]; then
  required_commands=(uv node npm)
else
  required_commands=(uv node npm screen curl)
fi
optional_commands=(lsof)
required_files=(
  "backend/pyproject.toml"
  "backend/uv.lock"
  "frontend/package.json"
  "frontend/package-lock.json"
)

missing=0

printf 'dev doctor: repository %s\n' "${REPO_ROOT}"

for command_name in "${required_commands[@]}"; do
  if command_path="$(command -v "${command_name}" 2>/dev/null)"; then
    printf '%s: %s\n' "${command_name}" "${command_path}"
  else
    printf 'missing: %s\n' "${command_name}"
    missing=1
  fi
done

for command_name in "${optional_commands[@]}"; do
  if command_path="$(command -v "${command_name}" 2>/dev/null)"; then
    printf '%s: %s\n' "${command_name}" "${command_path}"
  else
    printf 'optional missing: %s\n' "${command_name}"
  fi
done

for file_path in "${required_files[@]}"; do
  if [[ -f "${REPO_ROOT}/${file_path}" ]]; then
    printf 'file: %s\n' "${file_path}"
  else
    printf 'missing file: %s\n' "${file_path}"
    missing=1
  fi
done

if [[ "${missing}" -ne 0 ]]; then
  printf 'dev doctor: missing required tools\n'
  printf 'hint: install uv and Node.js/npm, or ensure $HOME/.local/bin is available on PATH.\n'
  exit 1
fi

printf 'dev doctor: ok\n'
