"""Command-line interface for cursor-mac-migrate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from cursor_mac_migrate import __version__
from cursor_mac_migrate.apply import apply_map, write_report
from cursor_mac_migrate.auto import build_auto_plan
from cursor_mac_migrate.detect import proposed_map, scan_tree
from cursor_mac_migrate.extensions import cursor_cli, iter_extensions, reinstall
from cursor_mac_migrate.lock import assert_cursor_closed
from cursor_mac_migrate.mapping import (
    default_dot_cursor,
    default_intellij,
    default_python,
    default_user_dir,
    dump_path_map,
    load_path_map,
    missing_mac_targets,
)
from cursor_mac_migrate.skills import list_skills


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cursor-mac-migrate",
        description=(
            "Remap a Cursor profile copied from Windows onto this Mac so "
            "agent sessions, skills, and multi-root workspaces keep working."
        ),
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    auto_p = sub.add_parser(
        "auto",
        help="Replace every C:\\Users\\<windows name> path with the same path under your Mac home",
    )
    _add_common(auto_p)
    auto_p.add_argument(
        "--also",
        action="append",
        default=[],
        help=r"Another folder pair, Windows=Mac. Example: C:\DevWorkspaces=/Users/jh/DevWorkspaces",
    )
    auto_p.add_argument("--windows-home", required=True, help=r"Example: C:\Users\janusz")
    auto_p.add_argument("--mac-home", default=str(Path.home()), help="Example: /Users/jh")
    auto_p.add_argument("--python", default=None, help="Mac python3, from: which python3")
    auto_p.add_argument("--intellij", default=None, help="Path ending in .app, or omit to auto-detect")
    auto_p.add_argument("--apply", action="store_true", help="Rewrite files. Without this, only a preview.")
    auto_p.add_argument("--allow-running", action="store_true")

    scan_p = sub.add_parser("scan", help="Find Windows paths still stored in the copied profile")
    _add_common(scan_p)
    scan_p.add_argument(
        "--write-map",
        type=Path,
        help="Write a starter path-map.json you can edit",
    )

    check_p = sub.add_parser("check-map", help="Validate path-map.json against folders on this Mac")
    _add_common(check_p)
    check_p.add_argument("--map", type=Path, required=True)

    apply_p = sub.add_parser(
        "apply",
        help="Rewrite chats, settings, workspace IDs, skills, and .code-workspace files",
    )
    _add_common(apply_p)
    apply_p.add_argument("--map", type=Path, required=True)
    apply_p.add_argument("--dry-run", action="store_true")
    apply_p.add_argument(
        "--allow-missing",
        action="store_true",
        help="Rewrite anyway even if some Mac repo paths do not exist yet",
    )
    apply_p.add_argument(
        "--allow-running",
        action="store_true",
        help="Do not abort if Cursor appears to be running (unsafe)",
    )
    apply_p.add_argument(
        "--report",
        type=Path,
        default=Path("migrate-report.json"),
    )

    verify_p = sub.add_parser("verify", help="Show leftover Windows paths, skills, and native extensions")
    _add_common(verify_p)
    verify_p.add_argument("--map", type=Path, required=False)

    ext_p = sub.add_parser(
        "reinstall-native-extensions",
        help="Force-reinstall extensions that shipped Windows native binaries",
    )
    _add_common(ext_p)
    ext_p.add_argument("--yes", action="store_true")

    keys_p = sub.add_parser(
        "mac-cmd-keybindings",
        help="For custom keybindings that only define ctrl, add a matching cmd binding",
    )
    _add_common(keys_p)
    keys_p.add_argument("--dry-run", action="store_true")
    keys_p.add_argument("--allow-running", action="store_true")

    args = parser.parse_args(argv)
    if args.cmd == "auto":
        return cmd_auto(args)
    if args.cmd == "scan":
        return cmd_scan(args)
    if args.cmd == "check-map":
        return cmd_check_map(args)
    if args.cmd == "apply":
        return cmd_apply(args)
    if args.cmd == "verify":
        return cmd_verify(args)
    if args.cmd == "reinstall-native-extensions":
        return cmd_reinstall(args)
    if args.cmd == "mac-cmd-keybindings":
        return cmd_keybindings(args)
    return 2


def _add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--user-dir",
        type=Path,
        default=default_user_dir(),
        help="Cursor User folder (default: ~/Library/Application Support/Cursor/User)",
    )
    parser.add_argument(
        "--dot-cursor",
        type=Path,
        default=default_dot_cursor(),
        help="~/.cursor folder",
    )


def cmd_auto(args: argparse.Namespace) -> int:
    user_dir = args.user_dir.expanduser()
    dot_cursor = args.dot_cursor.expanduser()
    if not user_dir.exists():
        print("The copied Cursor folder is not where the Mac expects it.")
        print("In Finder: Go → Go to Folder, then paste this and press Return:")
        print("  ~/Library/Application Support/Cursor/User")
        print("You should see settings.json in that folder. It is not there yet.")
        return 1
    mac_home = str(Path(args.mac_home).expanduser())
    desktop = Path(mac_home) / "Desktop"
    desktop.mkdir(parents=True, exist_ok=True)
    print("Reading the copied Cursor data. This can take a minute. Nothing is printed until it finishes.")
    scan = scan_tree(user_dir, dot_cursor)
    intellij = args.intellij if args.intellij else default_intellij()
    extra: list[tuple[str, str]] = []
    for item in args.also:
        if "=" not in item:
            print("Each --also value must look like C:\\DevWorkspaces=/Users/jh/DevWorkspaces")
            print(f"This one does not: {item}")
            return 1
        source, target = item.split("=", 1)
        extra.append((source, target))
    plan = build_auto_plan(
        scan,
        args.windows_home,
        mac_home,
        python=args.python or default_python(),
        intellij=intellij,
        user_dir=user_dir,
        dot_cursor=dot_cursor,
        extra_prefixes=extra,
    )
    map_path = desktop / "path-map.json"
    map_path.write_text(json.dumps(dump_path_map(plan.path_map), indent=2) + "\n", encoding="utf-8")
    (desktop / "cursor-migrate-ready.txt").write_text(
        "\n".join(plan.ready) + ("\n" if plan.ready else ""),
        encoding="utf-8",
    )
    (desktop / "cursor-migrate-missing.txt").write_text(
        "\n".join(plan.missing) + ("\n" if plan.missing else ""),
        encoding="utf-8",
    )
    (desktop / "cursor-migrate-outside-home.txt").write_text(
        "\n".join(plan.outside_home) + ("\n" if plan.outside_home else ""),
        encoding="utf-8",
    )

    print()
    print("These folder prefixes are rewritten everywhere:")
    for source, target in plan.prefixes:
        print(f"  {source}\\...  ->  {target}/...")
    print()
    print(f"Python the tool will write into settings: {plan.python or 'not found'}")
    if plan.intellij:
        print(f"IntelliJ the tool will write into settings: {plan.intellij}")
    else:
        print("IntelliJ was not found in /Applications. Project paths are still rewritten.")
        print("After you install IntelliJ, drag IntelliJ IDEA.app onto Terminal and rerun with --intellij and that path.")
    print()
    print(f"Skills already on this Mac: {len(plan.skills)}")
    print(f"Projects whose Mac folder already exists: {len(plan.ready)}")
    print(f"Projects not copied to the matching Mac folder yet: {len(plan.missing)}")
    print(f"Projects that were not under any prefix above: {len(plan.outside_home)}")
    print()
    print("The long lists are files on your Desktop, not in this window:")
    print(f"  {desktop / 'cursor-migrate-ready.txt'}")
    print(f"  {desktop / 'cursor-migrate-missing.txt'}")
    print(f"  {desktop / 'cursor-migrate-outside-home.txt'}")

    if not args.apply:
        print()
        print("No files were changed. Quit Cursor, then run the same command again with --apply at the end.")
        return 0

    assert_cursor_closed(allow_running=args.allow_running)
    report = apply_map(plan.path_map, dry_run=False, skip_missing=True)
    report_path = desktop / "cursor-migrate-report.json"
    write_report(report, report_path)
    attached = [item for item in report.relink.items if item.status in {"renamed", "unchanged-id"}]
    not_attached = [item for item in report.relink.items if item.status not in {"renamed", "unchanged-id", "skip"}]
    (desktop / "cursor-migrate-not-attached.txt").write_text(
        "\n".join(
            f"{item.status}\t{item.windows_uri}\t{item.mac_path}\t{item.detail}"
            for item in not_attached
        )
        + ("\n" if not_attached else ""),
        encoding="utf-8",
    )
    print()
    print(f"Rewrote the copied Cursor data. Backup: {report.backup_dir}")
    print(f"Chats attached to a Mac folder: {len(attached)}")
    print(f"Chats left unattached: {len(not_attached)}")
    if not_attached:
        print(f"  See {desktop / 'cursor-migrate-not-attached.txt'}")
    print(f"Text files updated: {len(report.files)}")
    print(f"Skills: {len(report.skills)}")
    print()
    print("Open Cursor. File → Open Folder, or File → Open Workspace from File for a .code-workspace.")
    print("The Windows chat for that project should be in the agent list.")
    return 0


def cmd_scan(args: argparse.Namespace) -> int:
    user_dir = args.user_dir.expanduser()
    dot_cursor = args.dot_cursor.expanduser()
    if not user_dir.exists():
        print(f"No Cursor User folder at {user_dir}", file=sys.stderr)
        print("Copy %APPDATA%\\Cursor\\User to that location first.", file=sys.stderr)
        return 1
    scan = scan_tree(user_dir, dot_cursor)
    print(f"Scanned {user_dir} and {dot_cursor}")
    print()
    print(f"Skills found: {len(scan.skills)}")
    for skill in scan.skills:
        print(f"  - {skill.name}  ({skill})")
    print()
    print(f"Workspaces Cursor knows about: {len(scan.workspace_uris)}")
    print("The full workspace list is not printed here, so it cannot flood the window.")
    print()
    if scan.python_hits:
        print("Python-looking Windows paths:")
        for item in scan.python_hits[:20]:
            print(f"  - {item}")
        print()
    if scan.intellij_hits:
        print("IntelliJ/JetBrains-looking Windows paths:")
        for item in scan.intellij_hits[:20]:
            print(f"  - {item}")
        print()
    top = scan.windows_paths.most_common(40)
    print(f"Unique Windows paths mentioned: {len(scan.windows_paths)}")
    print("A sample is below. The full list is not printed.")
    for path, count in top[:15]:
        print(f"  {count:5d}  {path}")
    print()
    if args.write_map:
        payload = proposed_map(scan, Path.home())
        payload["tools"]["python"] = default_python() or payload["tools"]["python"]
        payload["tools"]["intellij"] = default_intellij() or payload["tools"]["intellij"]
        payload["cursor_user_dir"] = str(user_dir)
        payload["dot_cursor"] = str(dot_cursor)
        args.write_map.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print()
        print(f"Wrote {args.write_map}")
        print("Edit every FILL_IN_MAC_PATH_FOR_* value, then run:")
        print(f"  python3 -m cursor_mac_migrate check-map --map {args.write_map}")
    else:
        print()
        print("Next: write a map file with")
        print("  python3 -m cursor_mac_migrate scan --write-map ./path-map.json")
    return 0


def cmd_check_map(args: argparse.Namespace) -> int:
    path_map = load_path_map(args.map)
    path_map.user_dir = args.user_dir.expanduser()
    path_map.dot_cursor = args.dot_cursor.expanduser()
    print(json.dumps(dump_path_map(path_map), indent=2))
    missing = missing_mac_targets(path_map)
    if not missing:
        print()
        print("All mapped Mac paths exist. You can apply:")
        print(f"  python3 -m cursor_mac_migrate apply --map {args.map} --dry-run")
        return 0
    print()
    print("Missing on this Mac:")
    for item in missing:
        print(f"  - {item}")
    print()
    print("Clone those repos / copy those .code-workspace files, or fix the map.")
    return 1


def cmd_apply(args: argparse.Namespace) -> int:
    assert_cursor_closed(allow_running=args.allow_running)
    path_map = load_path_map(args.map)
    path_map.user_dir = args.user_dir.expanduser()
    path_map.dot_cursor = args.dot_cursor.expanduser()
    report = apply_map(
        path_map,
        dry_run=args.dry_run,
        skip_missing=args.allow_missing,
    )
    write_report(report, args.report)
    print(("DRY RUN " if args.dry_run else "") + "Apply summary")
    print(f"  backup: {report.backup_dir or '(dry-run, no backup)'}")
    print(f"  workspaces processed: {len(report.relink.items)}")
    for item in report.relink.items:
        print(
            f"    [{item.status}] {item.kind} {item.old_id} → {item.new_id}"
        )
        print(f"         {item.mac_path or item.windows_uri}")
        if item.detail:
            print(f"         {item.detail}")
    print(f"  sqlite DBs rewritten: {len(report.sqlite)}")
    for line in report.sqlite:
        print(f"    {line}")
    print(f"  text files rewritten: {len(report.files)}")
    print(f"  project transcript folders renamed: {len(report.projects)}")
    print(f"  skills visible under ~/.cursor/skills: {len(report.skills)}")
    if report.warnings:
        print("  warnings:")
        for warn in report.warnings:
            print(f"    - {warn}")
    print()
    print(f"Full report: {args.report}")
    if args.dry_run:
        print("Looks good? Run without --dry-run. Cursor must stay quit.")
    else:
        print("Next:")
        print("  1. python3 -m cursor_mac_migrate verify --map", args.map)
        print("  2. python3 -m cursor_mac_migrate reinstall-native-extensions")
        print("  3. Open Cursor, then File → Open Workspace from File… for multi-repo workplaces")
        print("     or File → Open Folder for a single repo. Your Windows session should be in the sidebar.")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    user_dir = args.user_dir.expanduser()
    dot_cursor = args.dot_cursor.expanduser()
    scan = scan_tree(user_dir, dot_cursor)
    print("Skills on this Mac:")
    skills = list_skills(dot_cursor)
    if not skills:
        print("  (none found under ~/.cursor/skills)")
        print("  Copy %USERPROFILE%\\.cursor\\skills → ~/.cursor/skills if they are missing.")
    for skill in skills:
        print(f"  - {skill.name}")
    print()
    leftover = scan.windows_paths
    print(f"Windows paths still stored: {len(leftover)}")
    if leftover:
        desktop = Path.home() / "Desktop" / "cursor-migrate-still-windows.txt"
        desktop.write_text(
            "\n".join(f"{count}\t{path}" for path, count in leftover.most_common()) + "\n",
            encoding="utf-8",
        )
        print(f"  The list is in {desktop}")
        print("  It is not printed here.")
        status = 1
    else:
        print("  none — path rewrite looks complete.")
        status = 0
    print()
    native = [ext for ext in iter_extensions(dot_cursor) if ext.needs_reinstall]
    print(f"Extensions that should be reinstalled for macOS: {len(native)}")
    for ext in native:
        print(f"  - {ext.ext_id}  ({ext.reason})")
    if native:
        print("Run: python3 -m cursor_mac_migrate reinstall-native-extensions")
    print()
    cli = cursor_cli()
    print(f"cursor CLI: {cli or 'not found (install from Command Palette)'}")
    if args.map:
        path_map = load_path_map(args.map)
        missing = missing_mac_targets(path_map)
        if missing:
            print("Mapped Mac paths still missing:")
            for item in missing:
                print(f"  - {item}")
            status = 1
    return status


def cmd_reinstall(args: argparse.Namespace) -> int:
    dot_cursor = args.dot_cursor.expanduser()
    native = [ext for ext in iter_extensions(dot_cursor) if ext.needs_reinstall]
    if not native:
        print("No Windows-native extensions detected.")
        return 0
    ids = sorted({ext.ext_id for ext in native})
    print("Will force-reinstall:")
    for ext_id in ids:
        print(f"  - {ext_id}")
    if not args.yes:
        print("Re-run with --yes to execute.")
        return 0
    for ext_id, code, output in reinstall(ids):
        mark = "ok" if code == 0 else f"fail ({code})"
        print(f"[{mark}] {ext_id}")
        if output:
            print(output)
    return 0


def cmd_keybindings(args: argparse.Namespace) -> int:
    assert_cursor_closed(allow_running=args.allow_running)
    path = args.user_dir.expanduser() / "keybindings.json"
    if not path.exists():
        print(f"No {path}")
        return 0
    text = path.read_text(encoding="utf-8")
    # keybindings.json allows comments; strip a cheap subset.
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        print("keybindings.json has comments or trailing commas I cannot parse.")
        print("Edit it in Cursor: Cmd+K Cmd+S → Open Keyboard Shortcuts (JSON).")
        return 1
    changed = 0
    for item in data:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "")
        if "ctrl+" in key.lower() and not item.get("mac"):
            item["mac"] = _ctrl_to_cmd(key)
            changed += 1
    print(f"Bindings that need a Mac cmd equivalent: {changed}")
    if args.dry_run or not changed:
        return 0
    path.write_text(json.dumps(data, indent=4) + "\n", encoding="utf-8")
    print(f"Updated {path}")
    return 0


def _ctrl_to_cmd(key: str) -> str:
    return (
        key.replace("ctrl+", "cmd+")
        .replace("Ctrl+", "cmd+")
        .replace("CTRL+", "cmd+")
    )


if __name__ == "__main__":
    raise SystemExit(main())
