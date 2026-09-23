"""Rewrite Windows paths in Cursor JSON/markdown/text files."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from cursor_mac_migrate.paths import PathRewriter, looks_like_windows_path

TEXT_SUFFIXES = {
    ".json",
    ".jsonc",
    ".md",
    ".mdc",
    ".txt",
    ".yml",
    ".yaml",
    ".toml",
    ".code-workspace",
    ".cursorignore",
    ".css",
    ".js",
    ".ts",
    ".html",
}

SKIP_DIR_NAMES = {
    "Cache",
    "CachedData",
    "CachedExtensionVSIXs",
    "Code Cache",
    "GPUCache",
    "logs",
    "Crashpad",
    "Service Worker",
    "blob_storage",
    "node_modules",
    ".git",
    "extensions",
}


@dataclass
class FileRewriteStats:
    path: Path
    changed: bool
    reason: str = ""


def rewrite_file(path: Path, rewriter: PathRewriter, *, dry_run: bool = False) -> FileRewriteStats:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return FileRewriteStats(path, False, f"unreadable: {exc}")
    if b"\x00" in raw[:4096]:
        return FileRewriteStats(path, False, "binary")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            return FileRewriteStats(path, False, "not utf-8")
    new_text = _rewrite_text(path, text, rewriter)
    if new_text == text:
        return FileRewriteStats(path, False, "unchanged")
    if not dry_run:
        path.write_text(new_text, encoding="utf-8")
    return FileRewriteStats(path, True, "rewritten")


def _rewrite_text(path: Path, text: str, rewriter: PathRewriter) -> str:
    if path.suffix.lower() in {".json", ".code-workspace"} or path.name.endswith(".json"):
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return rewriter.rewrite_string(text)
        rewritten = rewriter.rewrite_obj(data)
        if rewritten == data:
            return text
        return json.dumps(rewritten, ensure_ascii=False, indent=2) + "\n"
    return rewriter.rewrite_string(text)


def iter_text_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    files: list[Path] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIR_NAMES or part.startswith("User.mac-migrate-backup") for part in path.parts):
            continue
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {
            "mcp.json",
            "hooks.json",
            "cli-config.json",
            "argv.json",
            "settings.json",
            "keybindings.json",
            "workspace.json",
            "storage.json",
        }:
            files.append(path)
            continue
        if path.suffix.lower() in {
            ".vscdb",
            ".db",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".webp",
            ".wasm",
            ".node",
            ".zip",
            ".pak",
            ".dll",
            ".exe",
            ".so",
            ".dylib",
        }:
            continue
        try:
            if path.stat().st_size > 2_000_000:
                continue
        except OSError:
            continue
        if scan_file_for_windows(path):
            files.append(path)
    return files


def scan_file_for_windows(path: Path) -> bool:
    try:
        raw = path.read_bytes()
    except OSError:
        return False
    if b"\x00" in raw[:1024]:
        return False
    try:
        text = raw.decode("utf-8", errors="ignore")
    except UnicodeDecodeError:
        return False
    return looks_like_windows_path(text)
