"""Find and open apps installed on this computer."""
import difflib
import json
import os
import platform
import re
import subprocess
import webbrowser
from pathlib import Path

SYSTEM = platform.system()


def _norm(name: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", name.lower()).strip()


class Apps:
    def __init__(self, cfg: dict):
        self.aliases = {_norm(k): str(v) for k, v in cfg["apps"].items()}
        self.installed = self._discover()  # display name -> how to launch it

    def names(self) -> list[str]:
        return sorted(set(self.installed) | set(self.aliases))

    # ---- discovery -------------------------------------------------------
    def _discover(self) -> dict:
        try:
            if SYSTEM == "Windows":
                return self._discover_windows()
            if SYSTEM == "Darwin":
                apps = {}
                for root in ("/Applications", "/System/Applications", str(Path.home() / "Applications")):
                    for p in Path(root).glob("*.app"):
                        apps[p.stem] = p.stem
                return apps
            apps = {}
            for root in ("/usr/share/applications", str(Path.home() / ".local/share/applications")):
                for p in Path(root).glob("*.desktop"):
                    m = re.search(r"^Name=(.+)$", p.read_text(errors="ignore"), re.M)
                    if m:
                        apps[m.group(1).strip()] = p.stem
            return apps
        except Exception as e:
            print(f"  (couldn't list installed apps: {e})")
            return {}

    def _discover_windows(self) -> dict:
        # Get-StartApps lists everything in the Start menu, including Store apps.
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Get-StartApps | ConvertTo-Json -Compress"],
            capture_output=True, text=True, timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        ).stdout
        items = json.loads(out or "[]")
        if isinstance(items, dict):
            items = [items]
        apps = {}
        for it in items:
            name = it.get("Name")
            if name and not re.search(r"uninstall|readme|help|documentation", name, re.I):
                apps[name] = it["AppID"]
        return apps

    # ---- opening ---------------------------------------------------------
    def find(self, spoken: str):
        """Return (display name, kind, target) for the best match, or None."""
        want = _norm(spoken)
        if not want:
            return None
        if want in self.aliases:
            return spoken, "alias", self.aliases[want]
        by_norm = {_norm(n): n for n in self.installed}
        if want in by_norm:
            n = by_norm[want]
            return n, "app", self.installed[n]
        # "chrome" -> "Google Chrome", "word" -> "Word"
        contains = [k for k in by_norm if re.search(rf"\b{re.escape(want)}\b", k)]
        if contains:
            n = by_norm[min(contains, key=len)]
            return n, "app", self.installed[n]
        close = difflib.get_close_matches(want, list(by_norm) + list(self.aliases), n=1, cutoff=0.72)
        if close:
            k = close[0]
            if k in self.aliases:
                return k, "alias", self.aliases[k]
            n = by_norm[k]
            return n, "app", self.installed[n]
        return None

    def open(self, spoken: str) -> str | None:
        """Open an app by spoken name. Returns its real name, or None if not found."""
        match = self.find(spoken)
        if not match:
            return None
        name, kind, target = match
        if kind == "alias":
            open_target(target)
        elif SYSTEM == "Windows":
            subprocess.Popen(["explorer.exe", f"shell:AppsFolder\\{target}"])
        elif SYSTEM == "Darwin":
            subprocess.Popen(["open", "-a", target])
        else:
            subprocess.Popen(["gtk-launch", target], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return name


def open_target(target: str):
    """Open a web address, file, folder or program."""
    if re.match(r"^https?://", target):
        webbrowser.open(target)
        return
    path = Path(os.path.expandvars(os.path.expanduser(target)))
    if SYSTEM == "Windows":
        os.startfile(str(path) if path.exists() else target)
    elif SYSTEM == "Darwin":
        subprocess.Popen(["open", str(path)] if path.exists() else ["open", "-a", target])
    else:
        subprocess.Popen(["xdg-open", str(path)] if path.exists() else [target])
