"""Load and validate the Windows → macOS path map."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from cursor_mac_migrate.paths import PathRewriter, Replacement, replacement_pairs, to_posix


@dataclass
class RootMap:
    windows: str
    mac: str
    kind: str = "folder"  # folder | workspace | home | tool


@dataclass
class PathMap:
    roots: list[RootMap] = field(default_factory=list)
    python: str | None = None
    intellij: str | None = None
    user_dir: Path | None = None
    dot_cursor: Path | None = None

    def rewriter(self, id_map: dict[str, str] | None = None) -> PathRewriter:
        pairs: list[Replacement] = []
        for root in sorted(self.roots, key=lambda item: len(item.windows), reverse=True):
            if _is_windows_path(root.windows) and root.mac:
                pairs.extend(replacement_pairs(root.windows, root.mac))
        extra: dict[str, str] = dict(id_map or {})
        return PathRewriter(
            pairs,
            extra_id_map=extra,
            python=self.python,
            intellij=self.intellij,
        )

    def mac_for_windows(self, windows_path: str) -> str | None:
        rewriter = self.rewriter()
        rewritten = rewriter.rewrite_string(windows_path)
        if rewritten == windows_path:
            # Try slash-normalized form.
            alt = rewriter.rewrite_string(windows_path.replace("/", "\\"))
            if alt != windows_path.replace("/", "\\"):
                return alt
            return None
        return rewritten


def _is_windows_path(value: str) -> bool:
    return len(value) >= 2 and value[1] == ":"


def default_user_dir() -> Path:
    return Path.home() / "Library" / "Application Support" / "Cursor" / "User"


def default_dot_cursor() -> Path:
    return Path.home() / ".cursor"


def default_python() -> str | None:
    found = shutil.which("python3") or shutil.which("python")
    return found


def default_intellij() -> str | None:
    apps = sorted(Path("/Applications").glob("IntelliJ IDEA*.app"))
    if apps:
        return str(apps[0])
    return None


def load_path_map(path: Path) -> PathMap:
    data = json.loads(path.read_text(encoding="utf-8"))
    roots: list[RootMap] = []
    homes = data.get("homes") or {}
    if homes.get("windows") and homes.get("mac"):
        roots.append(RootMap(homes["windows"], homes["mac"], "home"))
    for item in data.get("roots") or []:
        roots.append(
            RootMap(
                windows=item["windows"],
                mac=item["mac"],
                kind=item.get("kind", "folder"),
            )
        )
    for item in data.get("workspaces") or []:
        roots.append(
            RootMap(
                windows=item["windows"],
                mac=item["mac"],
                kind="workspace",
            )
        )
    tools = data.get("tools") or {}
    user_dir = data.get("cursor_user_dir")
    dot = data.get("dot_cursor")
    return PathMap(
        roots=roots,
        python=tools.get("python") or default_python(),
        intellij=tools.get("intellij") or default_intellij(),
        user_dir=Path(user_dir).expanduser() if user_dir else default_user_dir(),
        dot_cursor=Path(dot).expanduser() if dot else default_dot_cursor(),
    )


def dump_path_map(path_map: PathMap) -> dict:
    homes = next((r for r in path_map.roots if r.kind == "home"), None)
    workspaces = [r for r in path_map.roots if r.kind == "workspace"]
    roots = [r for r in path_map.roots if r.kind not in {"home", "workspace"}]
    return {
        "homes": {
            "windows": homes.windows if homes else "C:\\Users\\YOUR_WINDOWS_USER",
            "mac": homes.mac if homes else str(Path.home()),
        },
        "roots": [
            {"windows": r.windows, "mac": r.mac, "kind": r.kind} for r in roots
        ],
        "workspaces": [
            {"windows": r.windows, "mac": r.mac} for r in workspaces
        ],
        "tools": {
            "python": path_map.python or "/usr/bin/python3",
            "intellij": path_map.intellij or "/Applications/IntelliJ IDEA.app",
        },
        "cursor_user_dir": str(path_map.user_dir or default_user_dir()),
        "dot_cursor": str(path_map.dot_cursor or default_dot_cursor()),
    }


def missing_mac_targets(path_map: PathMap) -> list[str]:
    missing: list[str] = []
    for root in path_map.roots:
        mac = to_posix(root.mac)
        if not mac or mac.startswith("FILL_") or "YOUR_" in mac:
            missing.append(f"{root.windows} → (empty mac path)")
            continue
        target = Path(mac)
        if root.kind == "workspace":
            if not target.exists():
                missing.append(f"workspace file missing: {mac}")
        else:
            if not target.exists():
                missing.append(f"folder missing: {mac}")
    if path_map.python and not Path(path_map.python).exists():
        missing.append(f"python missing: {path_map.python}")
    return missing
