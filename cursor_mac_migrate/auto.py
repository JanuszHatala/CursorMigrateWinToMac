"""One home-folder mapping that covers every project under that user."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from cursor_mac_migrate.detect import ScanResult
from cursor_mac_migrate.mapping import PathMap, RootMap, default_intellij, default_python
from cursor_mac_migrate.paths import normalize_windows_path, to_posix
from cursor_mac_migrate.workspace_relink import file_uri_to_native


@dataclass
class AutoPlan:
    path_map: PathMap
    windows_home: str
    mac_home: str
    python: str | None
    intellij: str | None
    prefixes: list[tuple[str, str]] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    ready: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)
    outside_home: list[str] = field(default_factory=list)


def translate_prefixes(windows_path: str, prefixes: list[tuple[str, str]]) -> str | None:
    """Rewrite a Windows path using the longest matching prefix."""
    ordered = sorted(
        prefixes,
        key=lambda item: len(normalize_windows_path(item[0])),
        reverse=True,
    )
    for source, target in ordered:
        rewritten = translate_home(windows_path, source, target)
        if rewritten is not None:
            return rewritten
    return None


def translate_home(windows_path: str, windows_home: str, mac_home: str) -> str | None:
    """C:\\Users\\janusz\\Projects\\api -> /Users/jh/Projects/api."""
    win = normalize_windows_path(windows_path)
    home = normalize_windows_path(windows_home)
    if len(win) < 2 or win[1] != ":":
        return None
    if not win.lower().startswith(home.lower()):
        return None
    if len(win) > len(home) and win[len(home)] not in "\\/":
        return None
    suffix = win[len(home) :].replace("\\", "/")
    return to_posix(str(Path(mac_home)) + suffix)


def build_auto_plan(
    scan: ScanResult,
    windows_home: str,
    mac_home: str,
    *,
    python: str | None = None,
    intellij: str | None = None,
    user_dir: Path | None = None,
    dot_cursor: Path | None = None,
    extra_prefixes: list[tuple[str, str]] | None = None,
) -> AutoPlan:
    mac_home_path = str(Path(mac_home).expanduser())
    py = python or default_python()
    idea = intellij if intellij is not None else default_intellij()
    prefixes = [(normalize_windows_path(windows_home), mac_home_path)]
    for source, target in extra_prefixes or []:
        prefixes.append((normalize_windows_path(source), str(Path(target).expanduser())))
    prefixes.sort(key=lambda item: len(item[0]), reverse=True)
    path_map = PathMap(
        roots=[RootMap(source, target, "folder") for source, target in prefixes],
        python=py,
        intellij=idea,
        user_dir=user_dir,
        dot_cursor=dot_cursor,
    )
    plan = AutoPlan(
        path_map=path_map,
        windows_home=normalize_windows_path(windows_home),
        mac_home=mac_home_path,
        python=py,
        intellij=idea,
        prefixes=prefixes,
        skills=[path.name for path in scan.skills],
    )

    seen: set[str] = set()
    entries: list[tuple[str, str]] = []
    for _storage_id, kind, uri in scan.workspace_uris:
        native = file_uri_to_native(uri)
        entries.append((kind, native))
    for workspace in scan.code_workspaces:
        entries.append(("workspace", workspace))

    for kind, native in entries:
        key = normalize_windows_path(native) if len(native) >= 2 and native[1] == ":" else native
        if key in seen:
            continue
        seen.add(key)
        mac = translate_prefixes(native, prefixes)
        if mac is None:
            if len(native) >= 2 and native[1] == ":":
                plan.outside_home.append(normalize_windows_path(native))
            else:
                plan.outside_home.append(native)
            continue
        target = Path(mac)
        exists = target.exists()
        line = f"{native}  ->  {mac}"
        if exists:
            plan.ready.append(line)
            if kind == "workspace" or native.lower().endswith(".code-workspace"):
                path_map.roots.append(RootMap(normalize_windows_path(native), mac, "workspace"))
        else:
            plan.missing.append(line)
    return plan
