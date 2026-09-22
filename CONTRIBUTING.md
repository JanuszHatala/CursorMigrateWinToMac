# Contributing

## Branch workflow

Do not commit directly to `main`. Open a branch, push, and open a pull request.

```bash
git checkout -b cursor/your-change-7cee
# edit, commit, push
git push -u origin cursor/your-change-7cee
```

GitHub Actions must pass before merging. After the first setup, `main` should require pull requests and passing CI (see repository **Settings → Branches → Branch protection rules**).

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest
```
