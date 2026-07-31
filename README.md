# Hermes Proving Ground

Clean autonomous delivery proving ground for Hermes.

This repository is intentionally small at the start. Its purpose is to test whether Hermes can complete a repeatable software delivery loop without inherited branch debt, stale rescue records, or heavyweight infrastructure:

```text
task -> code -> tests -> PR -> CI -> merge -> deploy workflow -> healthcheck evidence
```

Overwatch Research remains the legacy hard-mode repository. This workspace is the clean-room benchmark.

## Local Validation

```powershell
$env:PYTHONPATH='backend'
py -3.11 -m pytest backend/tests --tb=short -p no:cacheprovider
py -3.11 -m app.health_server --check
```

## Rules For Hermes

- Complete one checklist item per PR.
- Update the exact source checklist item from `[ ]` to `[x]` only after implementation and tests pass.
- Keep tests local and deterministic.
- Do not introduce Redis, Celery, Docker, databases, model downloads, or external APIs unless a later task explicitly asks for them.
- Prefer simple Python modules and focused tests until the 10/10 benchmark is earned.
