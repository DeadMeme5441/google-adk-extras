---
title: Contributing
---

# Contributing

Thanks for your interest in improving Google ADK Extras!

## Dev Setup

```bash
git clone https://github.com/DeadMeme5441/google-adk-extras.git
cd google-adk-extras
uv sync   # or: pip install -e .[all]
```

## Tests

```bash
uv run pytest -q
```

## Guidelines

- Keep changes minimal and focused; match existing style.
- Add tests for new functionality.
- Update docs/examples when behavior changes.
- Avoid introducing unrelated formatting or refactors in PRs.

## PR Checklist

- [ ] Code compiles and tests pass
- [ ] New/changed docs included
- [ ] Backwards compatibility preserved
- [ ] Security considerations addressed (if applicable)

