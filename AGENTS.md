# AGENTS.md

Guidance for AI coding agents working in this repository. See `README.md`
for the human-facing overview; this file focuses on things that are easy to
get wrong automatically.

## What this is

Backend (Python/Flask) computes carpool driving plans from WebUntis
timetable data; frontend (React/Vite) is the UI for entering member/party
data and viewing/editing plans.

## Repo structure and submodule caveat

- `frontend/` is a **git submodule** pointing at a separate repository
  (`https://github.com/thabok/mycartime-frontend.git`), not a plain
  subdirectory.
  - `git status` in the superproject will show it as a single entity
    (modified/new commits), not individual file diffs.
  - To change code in it: edit files under `frontend/` normally, then
    commit *inside* it (`git -C frontend add -A && git -C frontend
    commit`). The superproject only tracks which commit hash the submodule
    points at — after committing inside the submodule, `git add frontend`
    in the superproject to record the new pointer.
  - Do not `git add`/commit individual files under `frontend/` from the
    superproject; that path is a gitlink, not a directory of trackable
    files.
  - Pushing submodule commits requires pushing from inside the submodule
    (`git -C frontend push origin main`) — the superproject's own push
    does not push submodule commits.
- Backend code under `backend/src/` uses **flat imports** (`import config`,
  `from solver_service import ...`), so it must be run with
  `backend/src` as the working directory / on `sys.path`, e.g. `cd
  backend/src && python app.py`. Running it as `python -m src.app` from
  `backend/` will fail with `ModuleNotFoundError: No module named 'config'`.

## Running / testing

- `./run.sh` from repo root starts both backend (port 1338) and frontend
  (port 8080, Vite, hot reload) together. Ctrl+C stops both.
- Backend has no auto-reload in this setup; after backend code changes,
  restart `./run.sh` (or just the backend process) to pick them up.
- Backend tests: `cd backend && source venv/bin/activate && python -m
  pytest test/`. `test/test_integration.py` requires the backend to be
  running already.
- There is no frontend test suite currently configured beyond
  `npm run lint`.

## The CP-SAT solver is slow to *prove* optimality

`backend/src/solver_service.py` (see `doc/ALGORITHM_EVOLUTION.md`) usually
*finds* the best plan for a realistic member set within a few seconds, but
proving no better plan exists can take around 3 minutes per plan. Running
plan generation in a batch (e.g. `backend/src/experiments/run_batch.py`, or
any script/loop that calls `SolverService`/`replay_capture.py` repeatedly)
will take a very long time unless you explicitly bound it - pass
`--max-seconds` (or `stop_after_no_improvement_seconds`, default 5s in
`config.SOLVER_STOP_AFTER_NO_IMPROVEMENT_SECONDS`) rather than letting each
run search to completion. In practice ~10 seconds per plan is enough to find
the actual optimum in almost all cases.

Because of this, avoid running or writing tests that exercise the solver
(anything that calls `SolverService.calculate_driving_plan` or replays a
capture) unless it's actually necessary for the task at hand - prefer
targeted unit tests over solver-driven ones, and when a solver-driven test is
genuinely needed, always cap its budget explicitly rather than relying on
defaults meant for interactive use.

## WebUntis dependency

There is no third-party WebUntis library. `backend/src/webuntis_client.py`
is a small hand-written JSON-RPC 2.0 client covering only what
`timetable_service.py` needs (login/logout, schoolyears, subject/room/class
name lookups, and a teacher's timetable looked up by name). Extend it
directly if new WebUntis endpoints are needed rather than reintroducing a
dependency on `python-webuntis` or similar.

## Conventions

- Don't add comments explaining *what* code does; only note non-obvious
  *why* (as in the rest of this file and `run.sh`).
- Match the existing code style in whichever file you're editing
  (backend is flat-import Python/Flask; frontend is TypeScript/React with
  shadcn/ui components).
- Sample/fixture data lives in `testdata/` and schemas in `schemas/` —
  check both when changing the driving-plan request/response shape.
