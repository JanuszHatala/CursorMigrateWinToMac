# Contributing

## Branch workflow

Do not commit directly to `main`. Open a branch, push, and open a pull request.

```bash
git checkout -b cursor/your-change-7cee
# edit, commit, push
git push -u origin cursor/your-change-7cee
```

GitHub Actions must pass before merging. The required status check name is **CI success** (aggregates Python 3.11 and 3.12 test jobs).

After the first push to GitHub, enable branch protection on `main` (require PR + **CI success**). Step-by-step: [docs/GITHUB_SETUP.md](docs/GITHUB_SETUP.md).

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest
```
