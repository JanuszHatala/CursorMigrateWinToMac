# Cursor Windows → macOS migrate

This is a small command-line tool you run **on the Mac after** you have already copied the Cursor profile. It does the part that a copy cannot do: rewrite Windows paths, recompute workspace IDs, and point historical agent sessions at the Mac folders.

## What "done" looks like

1. You open a repo (or a multi-root `.code-workspace`) on the Mac and the **same agent session you started on Windows** is in the sidebar, and you can keep chatting.
2. Skills that lived in `%USERPROFILE%\.cursor\skills` show up automatically (Customize → Skills).
3. A multi-repo workplace whose `.code-workspace` listed `C:\...` folders opens those same repos from their Mac paths.

Signing into Cursor is **not** enough for (1). Chats are local SQLite. Cursor keys them by a hash of the **absolute path**. `C:\Users\you\dev\api` and `/Users/you/dev/api` are different workspaces until this tool relinks them.

## Prerequisites

Do these on the Mac, Cursor fully quit (Cmd+Q, then Activity Monitor: no Cursor process).

Copied already (your steps 1 and 2):

| Windows | Mac |
| --- | --- |
| `%APPDATA%\Cursor\User` | `~/Library/Application Support/Cursor/User` |
| `%USERPROFILE%\.cursor` | `~/.cursor` |

Also:

- Cursor installed and signed in (User Rules in Customize → Rules come from the account).
- Every repo you care about **cloned on the Mac** at the paths you will put in the map.
- Every multi-root workplace file copied to a Mac path, for example `~/dev/platform.code-workspace`.

Do **not** open those folders in Cursor until after `apply`. Opening them first creates an empty Mac workspace ID and collides with the Windows one.

## Install the tool

```bash
cd /path/to/this/repo
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

Or run it without installing:

```bash
python3 -m cursor_mac_migrate --help
```

## The only commands you need

Replace paths if your clone of this repo lives somewhere else.

### 1. Scan what Windows left behind

```bash
python3 -m cursor_mac_migrate scan --write-map ./path-map.json
```

This prints:

- skills already under `~/.cursor/skills`
- every workspace Cursor stored (folder vs `.code-workspace`)
- Windows Python / IntelliJ hits
- a starter `path-map.json`

### 2. Fill in the Mac paths

Edit `path-map.json`. You only need **roots**: longest prefixes, plus each `.code-workspace` file.

```json
{
  "homes": {
    "windows": "C:\\Users\\Alice",
    "mac": "/Users/alice"
  },
  "roots": [
    {
      "windows": "C:\\Users\\Alice\\dev",
      "mac": "/Users/alice/dev",
      "kind": "folder"
    },
    {
      "windows": "D:\\work",
      "mac": "/Users/alice/work",
      "kind": "folder"
    }
  ],
  "workspaces": [
    {
      "windows": "C:\\Users\\Alice\\dev\\platform.code-workspace",
      "mac": "/Users/alice/dev/platform.code-workspace"
    }
  ],
  "tools": {
    "python": "/opt/homebrew/bin/python3",
    "intellij": "/Applications/IntelliJ IDEA.app"
  }
}
```

Rules:

- Use real, existing Mac folders. Check with `ls`.
- Map the parent of many repos once (`...\dev` → `~/dev`). Do not list every repo unless it lives on another drive.
- Put each multi-root `.code-workspace` under `workspaces` even if it already sits inside a mapped root.
- JSON strings need doubled backslashes: `"C:\\Users\\Alice"`.
- `tools.python` should be `which python3` on the Mac. Do not keep a copied Windows `python.exe`.
- `tools.intellij` should be the `.app` in `/Applications`. Do not keep `idea64.exe`.

See `path-map.example.json`.

### 3. Confirm the map

```bash
python3 -m cursor_mac_migrate check-map --map ./path-map.json
```

Fix anything listed as missing. Clone the repo or copy the `.code-workspace` file, then run check-map again.

### 4. Dry-run, then apply

```bash
python3 -m cursor_mac_migrate apply --map ./path-map.json --dry-run
python3 -m cursor_mac_migrate apply --map ./path-map.json
```

Apply will:

- refuse to run if Cursor is still open
- copy `state.vscdb` aside under `~/Library/Application Support/Cursor/User.mac-migrate-backup-...`
- rewrite Windows paths inside settings, MCP, skills, workspace files, and the chat databases
- rename `workspaceStorage/<old-id>` to the ID Cursor will compute on macOS (folder birth time + path, or lowercase path for `.code-workspace` files)
- patch `composer.composerHeaders` so sessions stay attached to the new ID
- rewrite Python/IntelliJ executable paths
- rename `~/.cursor/projects/...` transcript folders

If a Mac folder does not exist yet and you still want path rewrites:

```bash
python3 -m cursor_mac_migrate apply --map ./path-map.json --allow-missing
```

Chats for that folder will not attach until the folder exists and you run apply again.

### 5. Verify, then fix native extensions

```bash
python3 -m cursor_mac_migrate verify --map ./path-map.json
python3 -m cursor_mac_migrate reinstall-native-extensions --yes
```

`verify` must report **Windows paths still stored: 0** (or only paths you do not care about).

Python, Pylance, C++, PowerShell, and other extensions that shipped `win32` binaries will not work if you copied `~/.cursor/extensions` from Windows. Reinstall them on the Mac. Pure JS extensions (themes, most keybinding packs, IntelliJ **keybindings**) are fine as copied.

In Cursor on the Mac, run **Shell Command: Install `cursor` command in PATH** once if `reinstall-native-extensions` cannot find `cursor`.

### 6. Optional: Ctrl → Cmd for custom keybindings

Profile import usually does this. If you copied `keybindings.json` raw:

```bash
python3 -m cursor_mac_migrate mac-cmd-keybindings --dry-run
python3 -m cursor_mac_migrate mac-cmd-keybindings
```

That adds a `"mac": "cmd+..."` field wherever a custom binding only had `ctrl+`.

### 7. Open Cursor the right way

1. Start Cursor. Sign in.
2. Customize → Skills: your Windows skills should already be listed.
3. **Multi-repo workplace:** File → Open Workspace from File… → the Mac `.code-workspace`. Do not open a single inner folder and expect the multi-root chats.
4. **Single repo:** File → Open Folder → the Mac clone.
5. The Windows session should appear in the agent sidebar. Continue it.

If the list is empty, you opened a different path than the one in `path-map.json` (symlink, extra `Documents`, case). Run:

```bash
python3 -m cursor_mac_migrate scan
```

and compare the Mac path you opened with `mac_path` in `migrate-report.json`.

## Python and IntelliJ specifically

Do **not** try to reuse the Windows installs.

| Thing | What to do on Mac |
| --- | --- |
| CPython / pyenv / conda | Install with Homebrew or pyenv. Put `which python3` in `tools.python`. |
| `python.defaultInterpreterPath` in settings | The apply step overwrites Windows `.exe` paths with `tools.python`. Then pick the interpreter once in the Python extension. |
| Python / Pylance extensions | `reinstall-native-extensions`. The copied Windows VSIX will not load. |
| IntelliJ IDEA | Install the Mac `.app`. Point `tools.intellij` at it. |
| IntelliJ Keybindings extension | Usually copied as-is (no native binary). |
| JetBrains IDE remote / toolbox paths | Remap with a `roots` entry for `C:\\Program Files\\JetBrains` if scan still shows it. |

## Multi-root workplaces

A `.code-workspace` file is its own Cursor workspace. Chats belong to **that file's path**, not to the child repos.

On Windows it might have been:

```json
{
  "folders": [
    { "path": "C:\\Users\\Alice\\dev\\api" },
    { "path": "C:\\Users\\Alice\\dev\\web" }
  ]
}
```

Copy the file to the Mac (keep a stable path, for example `~/dev/platform.code-workspace`). Map it under `workspaces`. Apply rewrites the `folders` entries to the Mac repo paths. After that, opening **that file** restores the Windows sessions and `@`-mentions across those repos.

Relative folders (`"path": "../api"`) are left alone. Keep the same relative layout on the Mac.

## If apply reports `collision`

You opened the Mac folder in Cursor before relinking. Quit Cursor and:

```bash
# Example IDs come from migrate-report.json
USER="$HOME/Library/Application Support/Cursor/User/workspaceStorage"
mv "$USER/<mac-id>" "$USER/<mac-id>.empty-from-mac"
# rerun apply so the Windows folder can take the Mac id
python3 -m cursor_mac_migrate apply --map ./path-map.json
```

## Rollback

Apply writes `~/Library/Application Support/Cursor/User.mac-migrate-backup-<timestamp>/`. The original Windows copy is also still a backup if you kept it.

## What this tool will not do

- It will not invent Mac folders. Clone the git repos yourself.
- It will not sync chats through the Cursor account. That is local-only.
- It will not migrate Cloud Agent jobs; those already follow the account at [cursor.com/agents](https://cursor.com/agents).
- It will not copy SSH keys, git credentials, or Windows-only PATH entries.

## Tests

```bash
python3 -m pip install -e ".[dev]"
python3 -m pytest
```

## Safety notes

- Always quit Cursor before `apply`. Live SQLite (`state.vscdb-wal`) corrupts if rewritten while open.
- Work on the Mac copy. Keep the Windows `%APPDATA%\Cursor` tree untouched until a real session continues successfully.
- Cursor's workspace ID formula can change between versions. This tool matches current VS Code/Cursor behavior: folders use `md5(fsPath + birthtimeMs)` on macOS; `.code-workspace` files use `md5(lowercase path)`.
