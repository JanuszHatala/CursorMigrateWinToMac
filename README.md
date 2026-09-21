# Move Cursor from your Windows PC to your Mac

You already copied the Cursor folders. This page is the rest: make the Mac open the same AI chats, the same skills, and the same multi-repo workplaces.

You will use two apps on the Mac:

- **Terminal**. A window where you paste commands. The computer runs them and prints the answer underneath.
- **TextEdit**. To edit one settings file the tool writes for you.

You do not type paths from memory. Every path below is something a command prints, or a folder you drag from Finder.

Cursor on the Mac must stay **quit** until the last step. If it is open: click the word **Cursor** in the top menu bar, then **Quit Cursor**.

---

## 1. Open Terminal

1. Click the magnifying glass at the top right of the Mac screen, or press **Command** and **Space** together.
2. Type `Terminal`.
3. Press Return. A window opens with a blinking cursor. That is Terminal.

The folder Terminal is "standing in" matters. A command runs inside the current folder. You will see that folder change when you use `cd`.

To see the folder you are in, paste this and press Return:

```bash
pwd
```

`pwd` means "print working directory". It prints one line, for example:

```text
/Users/jan
```

That line is your Mac home folder. Yours will not say `jan`. It will say your Mac user name. Copy that line somewhere. You need it later.

Also paste:

```bash
whoami
```

That prints only the short name, for example `jan`. It is the last piece of the home folder.

---

## 2. Put this tool on the Desktop

This guide is a small program. It lives in a folder that contains:

- a file named `migrate.sh`
- a folder named `cursor_mac_migrate`

That folder has to be on the Mac. The Desktop is a fine place. The name of the folder can be anything. What matters is that those two items are inside it.

If you cloned or downloaded this project, the folder is wherever you put the download. In Finder, move that folder onto the Desktop so you can see it.

Then, in Terminal, paste these two lines, one at a time:

```bash
cd "$HOME/Desktop"
ls
```

`$HOME` is the folder `pwd` printed. You do not replace it. The Mac fills it in.

`ls` prints the names on the Desktop. Find the folder that contains this tool. Suppose `ls` shows a name `cursor-mac-migrate`. Go into it:

```bash
cd cursor-mac-migrate
ls
```

Use the name `ls` actually printed, not the example `cursor-mac-migrate`.

Check that you are in the right folder. The second `ls` must show `migrate.sh` and `cursor_mac_migrate`. If it does not, you are in the wrong folder. Run `cd "$HOME/Desktop"` again and pick the folder that does contain them.

`pwd` now prints something like:

```text
/Users/jan/Desktop/cursor-mac-migrate
```

Stay in this folder for every later command. If you close Terminal, open it again and `cd` back here before continuing.

---

## 3. Check that the copied Cursor files are really there

In Finder, click **Go** in the top menu bar, then **Go to Folder…**. Paste this and press Return:

```text
~/Library/Application Support/Cursor/User
```

You should see files named `settings.json` and `keybindings.json`, and folders named `globalStorage` and `workspaceStorage`. That is the copy of the Windows Cursor profile. If the folder is missing, the earlier copy did not land here. Stop and copy it again before going on.

Back in Terminal, paste:

```bash
ls "$HOME/Library/Application Support/Cursor/User"
ls "$HOME/.cursor/skills"
```

The second command lists your skills. Each skill is a folder that contains a file named `SKILL.md`. If this list is empty, the Windows `.cursor` folder was not copied to the Mac home folder. On Windows that folder is inside your user folder and is named `.cursor` (it is hidden). On the Mac it must be the hidden folder `~/.cursor`.

---

## 4. Install the tool, once

Still inside the tool folder (the one whose `ls` showed `migrate.sh`), paste this whole block:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

The first line creates a private Python folder named `.venv` inside the tool folder. The second line turns it on. Your prompt may start with `(.venv)`. The third line installs the tool into that private folder.

If macOS says `python3: command not found`, install Python from [https://www.python.org/downloads/macos/](https://www.python.org/downloads/macos/), close Terminal, open Terminal again, `cd` back into the tool folder, and run the three lines again.

You only do this once. Later, if the prompt does not start with `(.venv)`, run only:

```bash
source .venv/bin/activate
```

from inside the tool folder.

---

## 5. Let the tool list your Windows paths

Paste:

```bash
python3 -m cursor_mac_migrate scan --write-map "$HOME/Desktop/path-map.json"
```

Read the text it prints. It is your data, not an example:

- **Skills found** lists skills copied from Windows. Those are already on the Mac. Nothing else is required for skills, as long as this list matches what you had.
- **Workspaces Cursor knows about** lists every project and every multi-repo workplace Windows Cursor had open. Each line is a Windows location, for example `file:///c%3A/Users/Jan/source/api`.
- **Unique Windows paths** is the same information as plain Windows paths, for example `C:\Users\Jan\source\api`.

A new file appears on the Desktop: `path-map.json`. The tool already filled the Windows side from that scan. You will fill the Mac side.

Open it: in Finder, double-click `path-map.json` on the Desktop. If it opens in a browser or in Cursor, right-click it, choose **Open With**, then **TextEdit**.

---

## 6. What to type in `path-map.json`

The file is text in a format called JSON. Two rules:

- A Windows path uses backslashes. Inside this file every backslash is written twice. The real folder `C:\Users\Jan` is written `"C:\\Users\\Jan"`.
- A Mac path uses forward slashes, written once. `" /Users/jan "` with the quotes, no doubled slashes.

Do not invent a user name. Use the names the commands printed.

### `homes`

This is your personal folder on each computer. It is not a project.

On the Windows PC, open the Start menu, type `PowerShell`, and open **Windows PowerShell**. Paste:

```powershell
echo $env:USERPROFILE
```

It prints one line, for example `C:\Users\Jan`. That whole line is `homes.windows`. In the JSON file, double the backslashes:

```json
"windows": "C:\\Users\\Jan"
```

On the Mac you already ran `pwd` at the start, or run this again in Terminal:

```bash
echo "$HOME"
```

It prints one line, for example `/Users/jan`. That whole line is `homes.mac`, written with single slashes:

```json
"mac": "/Users/jan"
```

So if PowerShell printed `C:\Users\Jan` and the Mac printed `/Users/jan`, the block is:

```json
"homes": {
  "windows": "C:\\Users\\Jan",
  "mac": "/Users/jan"
}
```

Your names replace `Jan` and `jan`. They are often the same spelling. Sometimes they are not. Use what each computer printed.

### `roots`

A root is a parent folder that holds many projects, not one project.

Example, only if your real folders look like this:

- On Windows, projects live under `C:\Users\Jan\source`
- On the Mac, you put those same projects under `/Users/jan/source`

Then one root covers all of them:

```json
"roots": [
  {
    "windows": "C:\\Users\\Jan\\source",
    "mac": "/Users/jan/source",
    "kind": "folder"
  }
]
```

How to find the Windows side: look at the scan output. If many workspaces start with the same `C:\Users\Jan\source\...`, the common beginning `C:\Users\Jan\source` is the root.

How to find the Mac side:

1. In Finder, open the folder where you cloned or copied those projects.
2. Drag that folder from Finder into the Terminal window. Terminal inserts the full Mac path.
3. Copy that inserted path into `"mac"`.

If scan shows projects on two Windows drives, for example `C:\Users\Jan\source` and `D:\work`, add a second object in the `roots` list, with a comma between them. Each Windows parent gets the Mac folder you actually use for those projects.

Leave `"kind": "folder"` as written.

### `workspaces`

This is only for multi-repo workplaces: a file whose name ends in `.code-workspace`. One file lists several repos. Chats started in that workplace belong to that file, not to one repo inside it.

The scan lists these with `[workspace]` in front of the line.

On the Mac, that same file has to exist somewhere. Finder: **File → Find**, search for `code-workspace`. Or look in the folder where you copied it.

Drag the file onto Terminal to get its Mac path. Put the Windows path and the Mac path in the file:

```json
"workspaces": [
  {
    "windows": "C:\\Users\\Jan\\source\\platform.code-workspace",
    "mac": "/Users/jan/source/platform.code-workspace"
  }
]
```

If you have no `.code-workspace` files, leave `"workspaces": []`.

### `tools`

**Python.** In Terminal paste:

```bash
which python3
```

It prints one path, for example `/usr/bin/python3` or `/opt/homebrew/bin/python3`. Put that exact line in the file:

```json
"python": "/usr/bin/python3"
```

If the command prints nothing, Python is not installed. Install it, open a new Terminal, and run `which python3` again. Do not type a Windows path here. `python.exe` does not run on a Mac.

**IntelliJ.** Open Finder, then **Applications**. Look for an app named IntelliJ IDEA. Drag that app onto Terminal. You get a path that ends in `.app`, for example:

```text
/Applications/IntelliJ IDEA.app
```

Put that in the file:

```json
"intellij": "/Applications/IntelliJ IDEA.app"
```

If you do not have IntelliJ on the Mac, install it first, or leave the line as the scan wrote it and ignore IntelliJ until you install it.

### The two Cursor lines at the bottom

Leave these as the scan wrote them. They should already be your real Mac folders:

- `cursor_user_dir` is `~/Library/Application Support/Cursor/User`
- `dot_cursor` is `~/.cursor`

Save the file in TextEdit (**File → Save**).

---

## 7. Check the file, then apply it

Back in Terminal, in the tool folder, with `(.venv)` active:

```bash
python3 -m cursor_mac_migrate check-map --map "$HOME/Desktop/path-map.json"
```

If it says a folder is missing, that Mac path in the file does not exist. In Finder, confirm the project is really there, fix the path, save, and run `check-map` again.

When check-map says the paths exist, preview the rewrite:

```bash
python3 -m cursor_mac_migrate apply --map "$HOME/Desktop/path-map.json" --dry-run
```

Read the summary. Then run it for real. Cursor must still be quit.

```bash
python3 -m cursor_mac_migrate apply --map "$HOME/Desktop/path-map.json"
```

This rewrites the copied chat database so each Windows project points at the Mac folder, and it rewrites paths inside settings, skills, and `.code-workspace` files. It saves a backup next to the Cursor User folder. The name starts with `User.mac-migrate-backup-`.

Then:

```bash
python3 -m cursor_mac_migrate verify --map "$HOME/Desktop/path-map.json"
```

You want **Windows paths still stored: 0**, or only paths for projects you do not use anymore.

Extensions that contain Windows-only code (Python, C++, PowerShell, and similar) must be installed again for the Mac:

```bash
python3 -m cursor_mac_migrate reinstall-native-extensions --yes
```

If that says it cannot find `cursor`: open Cursor, press **Command Shift P**, type `Install 'cursor' command`, run **Shell Command: Install 'cursor' command in PATH**, quit Cursor again, and rerun the reinstall command.

Custom keyboard shortcuts that only say `ctrl` can get a Mac `cmd` copy:

```bash
python3 -m cursor_mac_migrate mac-cmd-keybindings
```

---

## 8. Open Cursor and continue the old chat

1. Open Cursor. Sign in with the same account. Rules you typed in **Customize → Rules** come from the account. You do not copy those by hand.
2. Open **Customize → Skills**. The skills listed by `scan` should be there.
3. For a normal project: **File → Open Folder…** and choose the Mac folder of that project.
4. For a multi-repo workplace: **File → Open Workspace from File…** and choose the `.code-workspace` file. Do not open one repo inside it if the chat was started from the workplace file.
5. The chat you started on Windows should be in the agent list on the left. Open it and send a new message.

That last step is the real test. The same conversation continues on the Mac.

If the list is empty, the folder you opened is not the folder written in `path-map.json`. A different spelling, an extra folder, or a shortcut (alias) counts as a different place. Run `scan` again and compare.

---

## Send me your real paths

If you want the next version of this file filled in with your names, paste the following. Each item says where to get it.

1. From the Mac Terminal, the output of:

```bash
whoami
echo "$HOME"
which python3
```

2. From Windows PowerShell, the output of:

```powershell
echo $env:USERPROFILE
```

3. The full text printed by:

```bash
python3 -m cursor_mac_migrate scan --write-map "$HOME/Desktop/path-map.json"
```

4. For each project you care about, the Mac folder. In Finder, open the project folder and drag it into Terminal. Paste those dropped paths, and say which Windows path from the scan each one matches.

5. For each multi-repo workplace, drag the `.code-workspace` file into Terminal and paste that path.

6. If IntelliJ is installed, drag **IntelliJ IDEA.app** from Applications into Terminal and paste that path. If it is not installed, say so.

I will put those values into the guide so you are not matching examples yourself.
