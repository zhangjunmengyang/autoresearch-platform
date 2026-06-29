from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "dev_doctor.sh"
WAIT_SCRIPT_PATH = REPO_ROOT / "scripts" / "wait_for_local_stack.sh"


def _write_fake_command(bin_dir: Path, name: str) -> None:
    path = bin_dir / name
    path.write_text("#!/bin/sh\nprintf '%s fake\\n' \"$0\"\n", encoding="utf-8")
    path.chmod(0o755)


def _doctor_env(tmp_path: Path, command_names: list[str]) -> dict[str, str]:
    home = tmp_path / "home"
    bin_dir = home / ".local" / "bin"
    bin_dir.mkdir(parents=True)
    for name in command_names:
        _write_fake_command(bin_dir, name)

    env = os.environ.copy()
    env["HOME"] = str(home)
    env["PATH"] = "/usr/bin:/bin"
    return env


def test_dev_doctor_uses_home_local_bin_for_local_toolchain(tmp_path):
    env = _doctor_env(tmp_path, ["uv", "node", "npm", "screen", "curl", "lsof"])

    result = subprocess.run(
        ["/bin/bash", str(SCRIPT_PATH)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "dev doctor: ok" in result.stdout
    assert f"uv: {tmp_path}/home/.local/bin/uv" in result.stdout
    assert f"npm: {tmp_path}/home/.local/bin/npm" in result.stdout


def test_dev_doctor_reports_missing_required_tool(tmp_path):
    env = _doctor_env(tmp_path, ["uv", "node", "screen", "curl", "lsof"])

    result = subprocess.run(
        ["/bin/bash", str(SCRIPT_PATH)],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "missing: npm" in result.stdout
    assert "dev doctor: missing required tools" in result.stdout


def test_wait_for_local_stack_retries_until_api_and_frontend_respond(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    state_file = tmp_path / "curl-count"
    curl_path = bin_dir / "curl"
    curl_path.write_text(
        f"""#!/bin/sh
count=0
if [ -f {state_file} ]; then
  count=$(cat {state_file})
fi
count=$((count + 1))
printf '%s' "$count" > {state_file}
if [ "$count" -lt 2 ]; then
  exit 7
fi
exit 0
""",
        encoding="utf-8",
    )
    curl_path.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:/usr/bin:/bin"
    env["DEV_WAIT_ATTEMPTS"] = "3"
    env["DEV_WAIT_SLEEP"] = "0"

    result = subprocess.run(
        ["/bin/bash", str(WAIT_SCRIPT_PATH), "8010", "5174"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "local stack ready" in result.stdout


def test_wait_for_local_stack_reports_logs_when_services_never_respond(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    curl_path = bin_dir / "curl"
    curl_path.write_text("#!/bin/sh\nexit 7\n", encoding="utf-8")
    curl_path.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:/usr/bin:/bin"
    env["DEV_WAIT_ATTEMPTS"] = "2"
    env["DEV_WAIT_SLEEP"] = "0"

    result = subprocess.run(
        ["/bin/bash", str(WAIT_SCRIPT_PATH), "8010", "5174"],
        cwd=REPO_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert "local stack unavailable" in result.stderr
    assert "logs/api.log" in result.stderr
    assert "logs/frontend.log" in result.stderr
