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
    fetch = _run_git(["fetch", REPO_URL, MAIN_BRANCH], timeout=45)
    current_log = _git_output(["log", f"-{LOG_LIMIT}", "--oneline", "--decorate"])
    latest_log = _git_output(["log", "--oneline", "--decorate", f"HEAD..{REMOTE_REF}"])
    current_revision = _git_output(["rev-parse", "--short", "HEAD"]).strip()
    latest_revision = _git_output(["rev-parse", "--short", REMOTE_REF]).strip() if fetch["ok"] else ""
    return {
        "repo_url": REPO_URL,
        "branch": MAIN_BRANCH,
        "fetch_ok": fetch["ok"],
        "fetch_output": fetch["output"],
        "has_update": bool(latest_log.strip()),
        "current_revision": current_revision,
        "latest_revision": latest_revision,
        "current_log": current_log,
        "latest_log": latest_log or "Đang ở phiên bản mới nhất.",
    }


def run_update() -> dict:
    before = _git_output(["rev-parse", "--short", "HEAD"]).strip()
    pull = _run_git(["pull", "--ff-only", REPO_URL, MAIN_BRANCH], timeout=90)
    after = _git_output(["rev-parse", "--short", "HEAD"]).strip()
    payload = {
        "repo_url": REPO_URL,
        "branch": MAIN_BRANCH,
        "ok": pull["ok"],
        "output": pull["output"],
        "before_revision": before,
        "after_revision": after,
        "updated": pull["ok"] and before != after,
        "current_log": _git_output(["log", f"-{LOG_LIMIT}", "--oneline", "--decorate"]),
        "restart_scheduled": False,
    }
    if pull["ok"]:
        payload["restart_scheduled"] = True
        _schedule_restart()
    return payload


def _run_git(args: list[str], timeout: int = 30) -> dict:
    try:
        completed = subprocess.run(
            ["git", *args],
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


def _schedule_restart() -> None:
    def restart() -> None:
        os.execv(sys.executable, [sys.executable, *sys.argv])

    threading.Timer(1.5, restart).start()
