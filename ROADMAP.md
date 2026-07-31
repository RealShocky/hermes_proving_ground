# Hermes Proving Ground Roadmap

## Goal

Prove Hermes can build a fresh software project from scratch with clean autonomous delivery discipline.

## Gate

The first release gate is a fresh strict `10 / 10`:

- 10 unique source checklist items.
- 10 unique PRs.
- 10 successful CI validations.
- 10 squash merges.
- 10 successful post-merge deploy workflow runs.
- 10 healthcheck evidence records.
- No manual repo repairs during the run.
- No duplicate task counting.
- No stale branch or dirty-worktree loops.

## Scope

This project starts as a tiny Python service with a deterministic healthcheck and pure-Python tests. It should grow only through small checklist items.

## Non-Goals

- No Celery or Redis in the initial gate.
- No Docker requirement in the initial gate.
- No database server requirement in the initial gate.
- No external model calls in the initial gate.
- No generated secrets or environment-specific credentials.

## After 10/10

After Hermes earns the clean-room gate, it can add controlled complexity:

- Persistence.
- API service runtime.
- Frontend shell.
- Containerization.
- Deployment target integration.
- Legacy Overwatch repair tasks.
