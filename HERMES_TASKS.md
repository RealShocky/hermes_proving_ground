# Hermes Proving Ground Tasks

Hermes reads unchecked checklist items here. Each item must be small enough for one autonomous coding round and one PR.

Use this format only:

```md
- [ ] Task description
```

Keep examples checked or inside prose so they are not executed accidentally.

- [x] Example only: replace this with a real unchecked task when ready.

---

## Phase 1 - Clean Delivery Baseline

- [ ] Add task model dataclass with id, title, status, created_at, and focused tests
- [ ] Add in-memory task repository with create, list, get, and update operations plus tests
- [ ] Add JSON file persistence adapter for tasks with deterministic temp-file tests
- [ ] Add task status transition validation for todo, in_progress, blocked, done with tests
- [ ] Add CLI command to create a task and print JSON output with tests
- [ ] Add CLI command to list tasks with status filtering and tests
- [ ] Add CLI command to mark a task done with tests
- [ ] Add audit log model for task changes with append-only tests
- [ ] Add health summary function reporting total and done task counts with tests
- [ ] Add version endpoint helper returning app name, version, and build metadata with tests

## Phase 2 - API And UI, Locked Until 10/10

- [ ] Add stdlib HTTP API route for listing tasks
- [ ] Add stdlib HTTP API route for creating tasks
- [ ] Add minimal static HTML dashboard showing task counts
- [ ] Add API healthcheck that includes version and task summary

## Phase 3 - Controlled Complexity, Locked Until Phase 2

- [ ] Add SQLite persistence adapter with migration tests
- [ ] Add Dockerfile and compose file with validation workflow coverage
- [ ] Add post-merge local deployment helper with pidfile cleanup
