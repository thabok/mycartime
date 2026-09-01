# AGENTS.md

Guidance for AI coding agents working in this repository. See `README.md`
for the human-facing overview; this file focuses on things that are easy to
get wrong automatically.

## What this is

Backend (Python/Flask) computes carpool driving plans from WebUntis
timetable data; frontend (React/Vite) is the UI for entering member/party
data and viewing/editing plans.

## Repo structure and submodule caveat

- `frontend/` and `webuntis/` are both **git submodules** pointing at
  separate repositories (`https://github.com/thabok/carpoolparty.git` and
  `https://github.com/thabok/python-webuntis` respectively), not plain
  subdirectories.
  - `git status` in the superproject will show each as a single entity
    (modified/new commits), not individual file diffs.
  - To change code in either: edit files under that directory normally,
    then commit *inside* it (e.g. `git -C frontend add -A && git -C
    frontend commit`, or `git -C webuntis add -A && git -C webuntis
    commit`). The superproject only tracks which commit hash the submodule
    points at — after committing inside the submodule, `git add
    frontend`/`git add webuntis` in the superproject to record the new
    pointer.
  - Do not `git add`/commit individual files under `frontend/` or
    `webuntis/` from the superproject; those paths are gitlinks, not
    directories of trackable files.
  - Pushing submodule commits requires pushing from inside the submodule
    (e.g. `git -C webuntis push origin main`) — the superproject's own push
    does not push submodule commits.
  - `webuntis/`'s own `.gitignore` already excludes `build/` and
    `*.egg-info/` (setuptools artifacts from local `pip install -e`) —
    don't commit those if they reappear.
- Backend code under `backend/src/` uses **flat imports** (`import config`,
  `from algorithm_service import ...`), so it must be run with
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

## WebUntis dependency

`backend/requirements.txt` intentionally does **not** list `webuntis` —
it's installed from the local submodule at `../webuntis` in editable mode
(see `run.sh`). If you add/restore a `webuntis>=...` line to
`backend/requirements.txt` pointing at PyPI, you will silently undo the
fork and likely break the backend's WebUntis connection approach. If you
need to update the fork, edit files under `webuntis/webuntis/` directly
and commit/push from inside the `webuntis/` submodule (see above).

## Conventions

- Don't add comments explaining *what* code does; only note non-obvious
  *why* (as in the rest of this file and `run.sh`).
- Match the existing code style in whichever file you're editing
  (backend is flat-import Python/Flask; frontend is TypeScript/React with
  shadcn/ui components).
- Sample/fixture data lives in `testdata/` and schemas in `schemas/` —
  check both when changing the driving-plan request/response shape.
