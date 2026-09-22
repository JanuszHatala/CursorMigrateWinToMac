# GitHub repository setup (maintainers)

Use this once after creating the empty repository [CursorMigrateWinToMac](https://github.com/JanuszHatala/CursorMigrateWinToMac.git).

## 1. Authenticate for push

Pick one method on a machine that has access to the repo.

**GitHub CLI (recommended)**

```bash
gh auth login
gh auth setup-git
```

**Personal access token (HTTPS)**

Create a classic PAT with `repo` scope, then:

```bash
git remote add github https://github.com/JanuszHatala/CursorMigrateWinToMac.git 2>/dev/null || true
git push -u github main
```

Git will prompt for username and password; use the PAT as the password.

## 2. First push from this project

From the repository root (branch `main` should contain the tool, tests, and `.github/workflows/ci.yml`):

```bash
git remote add github https://github.com/JanuszHatala/CursorMigrateWinToMac.git 2>/dev/null || true
git push -u github main
```

Optional: push the Cursor Cloud remote too if you use it:

```bash
git push -u origin main
```

## 3. Branch protection on `main`

In GitHub: **Settings → Branches → Add branch protection rule**

| Setting | Value |
| --- | --- |
| Branch name pattern | `main` |
| Require a pull request before merging | On (1 approval optional for solo maintainer) |
| Require status checks to pass before merging | On |
| Status checks that are required | **CI success** (wait until one CI run on `main` finishes so the name appears in the list) |
| Require branches to be up to date before merging | On |
| Do not allow bypassing the above settings | On (recommended) |
| Restrict who can push to matching branches | Optional: only bots / no one direct push |

After this, use the workflow in [CONTRIBUTING.md](../CONTRIBUTING.md): branch → push → pull request → merge when **CI success** is green.

## 4. Day-to-day pull request flow

```bash
git checkout main
git pull github main
git checkout -b cursor/my-change-7cee
# edit, commit
git push -u github cursor/my-change-7cee
gh pr create --base main --fill
gh pr checks --watch
gh pr merge --merge   # or --squash if you prefer
```

## 5. If CI badge is broken

The README badge points at `JanuszHatala/CursorMigrateWinToMac`. It turns green after the first successful workflow run on `main`.
