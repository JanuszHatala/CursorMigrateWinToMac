# CursorMigrateWinToMac

Point a Cursor profile you copied from Windows at the folders you use on macOS: agent threads, skills, settings, and multi-root workspaces.

Cursor does not sync local chat history with your account. Once `%APPDATA%\Cursor` and `%USERPROFILE%\.cursor` are on the Mac, Windows paths and workspace IDs are still wrong until you run this tool.

[![CI](https://github.com/JanuszHatala/CursorMigrateWinToMac/actions/workflows/ci.yml/badge.svg)](https://github.com/JanuszHatala/CursorMigrateWinToMac/actions/workflows/ci.yml)

## What you need before running the tool

| Item | Windows | macOS |
| --- | --- | --- |
| Cursor user data | `%APPDATA%\Cursor\User` | `~/Library/Application Support/Cursor/User` |
| Cursor home config (skills, MCP, extensions) | `%USERPROFILE%\.cursor` | `~/.cursor` |
| Your repositories | Often **not** under the user profile | Same layout you want on the Mac |

Example paths (Windows user `janusz`, Mac home `/Users/jh`):

- Windows projects: `C:\DevWorkspaces\acme\...`
- Mac projects: `/Users/jh/DevWorkspaces/acme/...`
- Windows user folder: `C:\Users\janusz` → Mac: `/Users/jh`

Sign in to Cursor on the Mac with the same account so **User Rules** in Customize → Rules sync. Chats and workspace storage are fixed by this tool, not by login.

## Migration overview

```text
Windows                         Mac (copy first)                After apply
---------------------------     ---------------------------     ---------------------------
%APPDATA%\Cursor\User         ~/Library/.../Cursor/User       paths + workspace IDs updated
%USERPROFILE%\.cursor          ~/.cursor                       skills/MCP paths updated
C:\DevWorkspaces\...           ~/DevWorkspaces/...             chats wired where folders exist
```

1. **On Windows:** quit Cursor, copy profile folders (see below).
2. **On Mac:** copy those folders into place, clone/copy **this repository**, install Python deps.
3. **Preview** (`auto` without `--apply`): writes reports into `migrate-work/` inside this tool folder; edit the rename and drop files there.
4. **Apply** (`auto` with `--apply`): attaches chats for **ready** paths and **accepted renames** only. Everything in **keep** stays unchanged.

Do **not** open important repos in Cursor on the Mac until after apply (or you get empty `workspaceStorage` collisions).

---

## Step 1: On Windows (manual)

1. **Quit Cursor** completely (File → Exit, check Task Manager: no `Cursor.app` / `Cursor.exe`).
2. Copy the **User** folder:
   - From: `%APPDATA%\Cursor\User`
   - To: USB / cloud / archive (you will place it on the Mac in step 2).
3. Copy the **`.cursor`** folder:
   - From: `%USERPROFILE%\.cursor`
   - To: same archive.
4. Copy your **code trees** (e.g. entire `C:\DevWorkspaces` → later `/Users/jh/DevWorkspaces`).
5. Optional but recommended: in Cursor on Windows, **Export Profile** (settings, keybindings, extensions) via Command Palette → **Preferences: Open Profiles (UI)** → Export. Import on the Mac after migration.

You do **not** need to copy:

- `AppData\Roaming\Cursor\Workspaces` or `glassMultiRootWorkspaces` unless you want old multi-root UI entries (the tool lists them as **cursor-internal** and leaves them alone).
- Git **worktrees** under `%USERPROFILE%\.cursor\worktrees` unless you still use those paths.

---

## Step 2: On Mac (manual placement)

1. Quit Cursor (**Cursor → Quit Cursor**). Activity Monitor may still show **CursorUIViewService**; that is a macOS pointer service, **not** the editor. You do not kill it.
2. Put the copied **User** folder here (merge/replace):

   ```text
   ~/Library/Application Support/Cursor/User
   ```

   Finder: **Go → Go to Folder…** → paste that path. You should see `settings.json`, `globalStorage`, `workspaceStorage`.

3. Put the copied **`.cursor`** folder at:

   ```text
   ~/.cursor
   ```

4. Put repositories where you want them long term, e.g.:

   ```text
   /Users/jh/DevWorkspaces/acme
   ```

5. Install [Cursor](https://cursor.com), sign in, optionally import the exported profile.

---

## Step 3: Install this tool

Use **one** of these on the Mac:

**A. Clone from GitHub (recommended after the repo is published)**

```bash
git clone https://github.com/JanuszHatala/CursorMigrateWinToMac.git
cd CursorMigrateWinToMac
```

**B. Copy the folder from Windows (no git on Windows)**

1. On Windows, copy the whole project folder (the one that contains `START-HERE.txt`, `migrate.sh`, `pyproject.toml`, and the `cursor_mac_migrate` package directory) to USB or cloud.
2. On the Mac, place it on the Desktop (or anywhere convenient).
3. Open Terminal and `cd` into that folder. Confirm:

   ```bash
   ls START-HERE.txt README.md pyproject.toml migrate.sh cursor_mac_migrate
   ```

   `START-HERE.txt` has the same preview/apply commands as below.

There is **no** folder named `cursor-mac-migrate`. The Python package lives in `cursor_mac_migrate/` (underscores). Commands use:

```bash
python3 -m cursor_mac_migrate
```

Install once:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

---

## Step 4: Preview (no changes to Cursor yet)

Replace `WINDOWS_USER` and paths with yours. Example for `janusz` / `jh` and `DevWorkspaces`:

```bash
python3 -m cursor_mac_migrate auto \
  --windows-home 'C:\Users\janusz' \
  --mac-home /Users/jh \
  --also 'C:\DevWorkspaces=/Users/jh/DevWorkspaces'
```

This scans copied SQLite databases and config files, then writes reports into `migrate-work/` next to this tool (override with `--report-dir`):

**Manual editing between preview and apply**

1. Open `cursor-migrate-rename-suggested.txt` and copy only the lines you agree with into `cursor-migrate-rename.txt` (create the file if needed). Add any paths the tool did not guess (Google Drive, `syncvault` → `sync-vault`, etc.).
2. Optionally add Windows paths to abandon in `cursor-migrate-drop.txt` (one full path per line).
3. Do **not** edit `cursor-migrate-keep.txt`; re-run preview after you copy more repos to the Mac.
4. Run **Step 5: Apply** only after you are happy with rename/drop files.

Report files:

| File | Meaning | You edit it? |
| --- | --- | --- |
| `cursor-migrate-ready.txt` | Mac folder exists at the mirrored path | No (they attach on apply) |
| `cursor-migrate-rename-suggested.txt` | Tool guessed a different Mac folder name | Copy chosen lines into `cursor-migrate-rename.txt` |
| `cursor-migrate-rename.txt` | **Accepted** Windows→Mac path pairs | Yes, one `Windows=Mac` line per row |
| `cursor-migrate-drop.txt` | Chats to **leave** as-is (abandon) | Yes, one Windows path per line |
| `cursor-migrate-keep.txt` | Not applied: missing copy, worktrees, Cursor-internal | No (informational) |
| `cursor-migrate-missing.txt` | Same as `[not-copied]` lines in keep | No |
| `cursor-migrate-outside-home.txt` | Paths outside `--windows-home` and `--also` | Fix mapping or ignore |

### Tags in `cursor-migrate-keep.txt`

- **`[not-copied]`**: mirrored Mac path does not exist yet. Copy/clone the project there, or add a manual line to `cursor-migrate-rename.txt`, then preview + apply again.
- **`[worktree]`**: Cursor/git worktree path you did not copy. Safe to ignore unless you recreate that worktree on the Mac.
- **`[cursor-internal]`**: Cursor’s own `AppData\Roaming\Cursor\...` workplace files. Per-repo chats in **ready** still work; combined “glass” workplaces from Windows will not reappear unless you copy those files too.

### Examples for `cursor-migrate-rename.txt`

**Different folder name** (`syncvault` on Windows, `sync-vault` on Mac):

```text
C:\DevWorkspaces\acme\syncvault=/Users/jh/DevWorkspaces/acme/sync-vault
```

**Google Drive** (Mac client uses `My Drive`):

```text
C:\Users\janusz\Google Drive\DEVs\AI\books&publications=/Users/jh/Google Drive/My Drive/DEVs/AI/books&publications
```

**Moved under another parent** (only if you really open the project from the right-hand path):

```text
C:\DevWorkspaces\acme\meterforge=/Users/jh/DevWorkspaces/acme/deploy-bundles/meterforge
```

Do **not** copy rename lines that point at old backups (`Acme-old`, `acme-copy`) unless you still use those folders.

`cursor-migrate-drop.txt` stays empty unless you want to permanently skip specific Windows paths (one full path per line).

---

## Step 5: Apply

Cursor must be quit. Use the same `auto` command with your rename/drop files:

```bash
python3 -m cursor_mac_migrate auto \
  --windows-home 'C:\Users\janusz' \
  --mac-home /Users/jh \
  --also 'C:\DevWorkspaces=/Users/jh/DevWorkspaces' \
  --renames migrate-work/cursor-migrate-rename.txt \
  --drop migrate-work/cursor-migrate-drop.txt \
  --apply
```

Apply also rewrites named multi-folder workspaces stored beside the User folder (`glassMultiRootWorkspaces` and `Workspaces`). Those are the lists behind the Add Folders dialog. The dialog's Save button stays disabled when the stored folder does not exist on the Mac, so edit the file with the tool instead of that dialog.

If apply stops with *"Cursor is still running"* but only **CursorUIViewService** appears in Activity Monitor, add:

```bash
  --allow-running
```

Apply only rewires:

- Paths in settings, MCP, skills, and chat databases for **ready** + **rename** entries.
- `workspaceStorage` IDs for folders that exist on the Mac.

It creates a backup next to the User folder: `User.mac-migrate-backup-<timestamp>/`.

Then reinstall native extensions (Python, C++, etc.):

```bash
python3 -m cursor_mac_migrate reinstall-native-extensions --yes
```

Install the `cursor` CLI from Cursor once if that command cannot find it: Command Palette → **Shell Command: Install 'cursor' command in PATH**.

Optional: map Ctrl shortcuts to Cmd:

```bash
python3 -m cursor_mac_migrate mac-cmd-keybindings
```

---

## Step 6: Open projects on the Mac

1. Start Cursor (signed in).
2. Open **Customize → Skills** and confirm skills under `~/.cursor/skills` should appear.
3. **Single repo:** **File → Open Folder** → e.g. `/Users/jh/DevWorkspaces/acme/radar-app`.
4. **Multi-root workplace:** **File → Open Workspace from File…** → choose the `.code-workspace` file on the Mac.

The Windows agent session for that workspace should show in the sidebar. If not, you opened a different path than the one in `ready` / `rename` (symlink, typo, or wrong parent).

---

## Command reference

```bash
# Preview. Lists go to migrate-work/ inside this folder.
python3 -m cursor_mac_migrate auto --windows-home 'C:\Users\janusz' --mac-home /Users/jh \
  --also 'C:\DevWorkspaces=/Users/jh/DevWorkspaces'

# Apply with selective renames/drops
python3 -m cursor_mac_migrate auto ... --renames migrate-work/cursor-migrate-rename.txt \
  --drop migrate-work/cursor-migrate-drop.txt --apply [--allow-running]

# After apply
python3 -m cursor_mac_migrate verify
python3 -m cursor_mac_migrate reinstall-native-extensions --yes
```

Lower-level commands (`scan`, `check-map`, `apply --map path-map.json`) still exist for advanced `path-map.json` workflows; most users only need `auto`.

---

## Troubleshooting

| Problem | What to do |
| --- | --- |
| Huge Terminal scroll from `scan` | Use `auto` instead; lists go to `migrate-work/`. |
| Many lines in `missing` / `keep` | Copy repos to the Mac path on the right, or add `cursor-migrate-rename.txt` lines, preview again, apply again. |
| `syncvault` not in rename-suggested | Add the `syncvault` → `sync-vault` line manually if the Mac folder exists. |
| `config` vs `ws-config` | `acme\config` in **ready** is the normal repo folder; `worktrees\config\...` in **keep** is a worktree, not a rename of `config`. |
| Apply blocked by CursorUIViewService | Use `--allow-running` (editor is already quit). |
| Empty chat list after open | Path mismatch; run preview again and compare with the folder you opened. |
| Collision / duplicate workspaceStorage | You opened the folder on the Mac before apply; see `cursor-migrate-not-attached.txt` after apply or move aside the empty Mac `workspaceStorage` id and re-apply. |
| Add Folders still shows `c:/...` and Save stays grey | Quit Cursor, then run `fix-workspaces` (below). |

---

## Already migrated, but a workspace still shows a Windows path

Quit Cursor (Cmd+Q). Then, from this repository:

```bash
python3 -m cursor_mac_migrate fix-workspaces \
  --windows-home 'C:\Users\janusz' \
  --mac-home /Users/jh \
  --also 'C:\DevWorkspaces=/Users/jh/DevWorkspaces' \
  --renames migrate-work/cursor-migrate-rename.txt
```

This rewrites leftover Windows paths in named workspaces, `.code-workspace` files inside your repos, profile text files, and every Cursor state database (including compressed values and the Glass project list). It does not move chat databases again. If a Windows path is still stored, the command prints it and exits with an error. Open Cursor afterward and check the folder list. Run it again after `git pull` if an earlier run only fixed some workspaces.

## Development

```bash
pip install -e ".[dev]"
python -m pytest
```

See [CONTRIBUTING.md](CONTRIBUTING.md). Changes go through pull requests; CI must pass on `main`.

Maintainers: first-time push and branch protection for GitHub are documented in [docs/GITHUB_SETUP.md](docs/GITHUB_SETUP.md).

## License

MIT. See [LICENSE](LICENSE).
