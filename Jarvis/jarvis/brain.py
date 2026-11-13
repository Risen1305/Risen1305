"""Jarvis's brain: Claude, via your Claude Code login (`claude -p`)."""
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from .config import DATA_DIR

SCHEMA = {
    "type": "object",
    "properties": {
        "say": {"type": "string", "description": "What Jarvis says out loud."},
        "open_apps": {
            "type": "array", "items": {"type": "string"},
            "description": "Exact names from the installed-apps list to open. Empty if none.",
        },
        "open_urls": {
            "type": "array", "items": {"type": "string"},
            "description": "Full https:// web addresses to open in the browser. Empty if none.",
        },
        "end_conversation": {
            "type": "boolean",
            "description": "True when the user is done (thanks, goodbye, that's all).",
        },
    },
    "required": ["say", "open_apps", "open_urls", "end_conversation"],
    "additionalProperties": False,
}

SYSTEM_PROMPT = """You are Jarvis, a voice assistant running on {title_cap}'s own computer. \
You speak with the calm, dry, impeccably polite manner of an English butler. Address the user as "{title}".

Everything you write in "say" is read aloud by a text-to-speech voice, so:
- Keep it brief: one to three short sentences unless asked for detail.
- Plain spoken English only. No markdown, lists, emoji, code, or URLs read out.
- Write numbers and units the way you'd say them.

You can open things on this computer:
- To open an app, put its exact name from the list below in "open_apps", and say so briefly ("Opening Spotify, {title}.").
- To open a website, put its full https:// address in "open_urls".
- If the user asks for an app that isn't in the list, say you couldn't find it. Never invent app names.
You cannot see the screen, read files, or control apps beyond opening them; if asked, say so plainly.
Set "end_conversation" to true when the user signals they're finished.

Installed apps: {apps}
"""


def find_claude() -> str:
    found = shutil.which("claude")
    if found:
        return found
    for p in (Path.home() / ".local/bin/claude.exe", Path.home() / ".local/bin/claude"):
        if p.exists():
            return str(p)
    raise RuntimeError(
        "Claude Code isn't installed or isn't on your PATH. Install it in PowerShell with:\n"
        "  irm https://claude.ai/install.ps1 | iex\n"
        "then run `claude` once to log in."
    )


class Brain:
    def __init__(self, cfg: dict, app_names: list[str]):
        b = cfg["brain"]
        title = cfg["user"].get("title", "sir")
        self.claude = find_claude()
        self.model = b.get("model", "")
        self.effort = b.get("effort", "low")
        apps = ", ".join(app_names)
        if len(apps) > 8000:  # keep the command line within Windows limits
            apps = apps[:8000].rsplit(",", 1)[0] + ", and others"
        self.system_prompt = SYSTEM_PROMPT.format(title=title, title_cap=title.capitalize(), apps=apps or "(none found)")
        self.session_id = None
        self.workdir = DATA_DIR / "brain"
        self.workdir.mkdir(parents=True, exist_ok=True)

    def ask(self, text: str, extra_context: str = "") -> dict:
        now = datetime.now().strftime("%A %d %B %Y, %H:%M")
        prompt = f"[{now}. {extra_context}]\n{text}" if extra_context else f"[{now}]\n{text}"
        cmd = [
            self.claude, "-p",
            "--output-format", "json",
            "--tools", "",
            "--json-schema", json.dumps(SCHEMA),
            "--system-prompt", self.system_prompt,
        ]
        if self.model:
            cmd += ["--model", self.model]
        if self.effort:
            cmd += ["--effort", self.effort]
        if self.session_id:
            cmd += ["--resume", self.session_id]
        try:
            proc = subprocess.run(
                cmd, input=prompt, capture_output=True, text=True, encoding="utf-8",
                cwd=self.workdir, timeout=120,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                env={**os.environ, "NO_COLOR": "1"},
            )
        except subprocess.TimeoutExpired:
            return _reply("I'm afraid that took too long. Shall we try again?")
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError:
            err = (proc.stderr or proc.stdout).strip()
            if "login" in err.lower() or "auth" in err.lower():
                return _reply("I'm not signed in to Claude. Please run claude in a terminal and log in.")
            print(f"  (Claude error: {err[:500]})")
            return _reply("My apologies, something went wrong reaching my brain.")
        if data.get("is_error"):
            print(f"  (Claude error: {data.get('result')})")
            if self.session_id:  # a broken session can't be resumed; start fresh next time
                self.session_id = None
            return _reply("My apologies, I couldn't think that through. Please try again.")
        self.session_id = data.get("session_id") or self.session_id
        out = data.get("structured_output")
        if not isinstance(out, dict):
            try:
                out = json.loads(data.get("result", ""))
            except (TypeError, json.JSONDecodeError):
                out = {"say": str(data.get("result", ""))}
        return {**_reply(""), **out}

    def forget(self):
        """Start a fresh conversation next time."""
        self.session_id = None


def _reply(say: str) -> dict:
    return {"say": say, "open_apps": [], "open_urls": [], "end_conversation": False}
