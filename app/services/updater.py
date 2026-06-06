from __future__ import annotations

import os
import subprocess
import sys
import threading
from pathlib import Path


REPO_URL = "https://github.com/daihieptn97/HomeNetControl.git"
REMOTE_REF = "FETCH_HEAD"
MAIN_BRANCH = "main"
LOG_LIMIT = "12"
REPO_DIR = Path(__file__).resolve().parents[2]


def update_status() -> dict:
    repo_ok = _is_git_repo()
    fetch = _run_git(["fetch", REPO_URL, MAIN_BRANCH], timeout=45) if repo_ok else {
        "ok": False,
        "output": f"{REPO_DIR} không phải git repository",
    }
    current_log = _git_text(["log", f"-{LOG_LIMIT}", "--oneline", "--decorate"])
    latest_log_result = _run_git(["log", "--oneline", "--decorate", f"HEAD..{REMOTE_REF}"]) if fetch["ok"] else {"ok": False, "output": ""}
    current_revision = _git_text(["rev-parse", "--short", "HEAD"]).strip()
    latest_revision = _git_text(["rev-parse", "--short", REMOTE_REF]).strip() if fetch["ok"] else ""
    status = _git_text(["status", "--short"])
    diagnostics = "\n".join(
        part
        for part in [
            fetch["output"],
            "" if latest_log_result["ok"] else latest_log_result["output"],
        ]
        if part
    )
    return {
        "repo_url": REPO_URL,
        "repo_dir": str(REPO_DIR),
        "branch": MAIN_BRANCH,
        "repo_ok": repo_ok,
        "fetch_ok": fetch["ok"],
        "fetch_output": diagnostics,
        "has_update": latest_log_result["ok"] and bool(latest_log_result["output"].strip()),
        "dirty": bool(status.strip()),
        "git_status": status or "Working tree clean.",
        "current_revision": current_revision,
        "latest_revision": latest_revision,
        "current_log": current_log or "Không đọc được git log hiện tại.",
        "latest_log": latest_log_result["output"] if latest_log_result["ok"] and latest_log_result["output"] else "Đang ở phiên bản mới nhất.",
    }


def run_update() -> dict:
    before = _git_text(["rev-parse", "--short", "HEAD"]).strip()
    fetch = _run_git(["fetch", REPO_URL, MAIN_BRANCH], timeout=45)
    if not fetch["ok"]:
        return _update_payload(False, before, before, fetch["output"], False)

    pull = _run_git(["pull", "--rebase", "--autostash", REPO_URL, MAIN_BRANCH], timeout=120)
    after = _git_text(["rev-parse", "--short", "HEAD"]).strip()
    output = "\n".join(part for part in [fetch["output"], pull["output"]] if part)
    deps = {"ok": True, "output": ""}
    if pull["ok"]:
        deps = _install_requirements()
        if deps["output"]:
            output = "\n".join(part for part in [output, deps["output"]] if part)
    payload = _update_payload(pull["ok"] and deps["ok"], before, after, output, pull["ok"] and deps["ok"])
    return payload


def _update_payload(ok: bool, before: str, after: str, output: str, schedule_restart: bool) -> dict:
    payload = {
        "repo_url": REPO_URL,
        "repo_dir": str(REPO_DIR),
        "branch": MAIN_BRANCH,
        "ok": ok,
        "output": output,
        "before_revision": before,
        "after_revision": after,
        "updated": ok and before != after,
        "current_log": _git_text(["log", f"-{LOG_LIMIT}", "--oneline", "--decorate"]),
        "git_status": _git_text(["status", "--short"]) or "Working tree clean.",
        "restart_scheduled": False,
    }
    if schedule_restart:
        payload["restart_scheduled"] = True
        _schedule_restart()
    return payload


def _run_git(args: list[str], timeout: int = 30) -> dict:
    try:
        completed = subprocess.run(
            ["git", "-c", f"safe.directory={REPO_DIR}", *args],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except Exception as exc:
        return {"ok": False, "output": str(exc)}
    output = "\n".join(part.strip() for part in [completed.stdout, completed.stderr] if part.strip())
    return {"ok": completed.returncode == 0, "output": output}


def _git_output(args: list[str]) -> str:
    return _run_git(args)["output"]


def _git_text(args: list[str]) -> str:
    result = _run_git(args)
    return result["output"] if result["ok"] else ""


def _is_git_repo() -> bool:
    return _run_git(["rev-parse", "--is-inside-work-tree"])["ok"]


def _install_requirements() -> dict:
    requirements = REPO_DIR / "requirements.txt"
    if not requirements.exists():
        return {"ok": True, "output": "Không có requirements.txt để cài đặt."}
    try:
        completed = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements)],
            cwd=REPO_DIR,
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except Exception as exc:
        return {"ok": False, "output": str(exc)}
    output = "\n".join(part.strip() for part in [completed.stdout, completed.stderr] if part.strip())
    return {"ok": completed.returncode == 0, "output": output}


def _schedule_restart() -> None:
    def restart() -> None:
        os.execv(sys.executable, [sys.executable, *sys.argv])

    threading.Timer(1.5, restart).start()
