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

- [x] Add task model dataclass with id, title, status, created_at, and focused tests
- [x] Add in-memory task repository with create, list, get, and update operations plus tests
- [x] Add JSON file persistence adapter for tasks with deterministic temp-file tests
- [x] Add task status transition validation for todo, in_progress, blocked, done with tests
- [x] Add CLI command to create a task and print JSON output with tests
- [x] Add CLI command to list tasks with status filtering and tests
- [x] Add CLI command to mark a task done with tests
- [x] Add audit log model for task changes with append-only tests
- [x] Add health summary function reporting total and done task counts with tests
- [x] Add version endpoint helper returning app name, version, and build metadata with tests

## Phase 2 - API And UI, Locked Until 10/10

- [x] Add stdlib HTTP API route for listing tasks
- [x] Add stdlib HTTP API route for creating tasks
- [x] Add minimal static HTML dashboard showing task counts
- [x] Add API healthcheck that includes version and task summary

## Phase 3 - Controlled Complexity, Locked Until Phase 2

- [ ] Add SQLite persistence adapter with migration tests
- [x] Add Dockerfile and compose file with validation workflow coverage
- [ ] Add post-merge local deployment helper with pidfile cleanup
