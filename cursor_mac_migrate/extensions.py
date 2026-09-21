"""Detect Windows-native extensions that need a Mac reinstall."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

NATIVE_HINTS = ("win32", "windows", ".node", ".dll", ".exe")
LIKELY_NATIVE_IDS = {
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-vscode.cpptools",
    "ms-dotnettools.csharp",
    "rust-lang.rust-analyzer",
    "ms-vscode.cmake-tools",
    "vadimcn.vscode-lldb",
    "ms-vscode.powershell",
}


@dataclass
class ExtensionInfo:
    ext_id: str
    path: Path
    needs_reinstall: bool
    reason: str


def cursor_cli() -> str | None:
    candidates = [
        Path("/usr/local/bin/cursor"),
        Path("/opt/homebrew/bin/cursor"),
        Path.home() / "Applications/Cursor.app/Contents/Resources/app/bin/cursor",
        Path("/Applications/Cursor.app/Contents/Resources/app/bin/cursor"),
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    found = subprocess.run(
        ["which", "cursor"], capture_output=True, text=True, check=False
    )
    if found.returncode == 0 and found.stdout.strip():
        return found.stdout.strip()
    return None


def iter_extensions(dot_cursor: Path) -> list[ExtensionInfo]:
    root = dot_cursor / "extensions"
    if not root.is_dir():
        return []
    found: list[ExtensionInfo] = []
    for manifest in root.glob("*/package.json"):
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        publisher = str(data.get("publisher") or "")
        name = str(data.get("name") or manifest.parent.name)
        ext_id = f"{publisher}.{name}".lower() if publisher else manifest.parent.name.lower()
        folder = manifest.parent.name.lower()
        reason = ""
        needs = False
        if "win32" in folder or folder.endswith("-windows"):
            needs = True
            reason = "extension folder is a Windows build"
        elif any(ext_id.startswith(native) for native in LIKELY_NATIVE_IDS):
            needs = True
            reason = "ships native binaries; reinstall the darwin build"
        else:
            for hint in ("win32-x64", "win32-arm64"):
                if (manifest.parent / hint).exists():
                    needs = True
                    reason = f"contains {hint}"
                    break
        found.append(ExtensionInfo(ext_id, manifest.parent, needs, reason))
    return found


def reinstall(ext_ids: list[str]) -> list[tuple[str, int, str]]:
    cli = cursor_cli()
    if not cli:
        raise SystemExit(
            "Could not find the `cursor` CLI. In Cursor on Mac: Command Palette → "
            "'Shell Command: Install cursor command in PATH'."
        )
    results: list[tuple[str, int, str]] = []
    for ext_id in ext_ids:
        proc = subprocess.run(
            [cli, "--install-extension", ext_id, "--force"],
            capture_output=True,
            text=True,
            check=False,
        )
        results.append((ext_id, proc.returncode, (proc.stdout + proc.stderr).strip()))
    return results
