# Testing Guide

All test scripts live in `backend/test/` and expect real request data at `testdata/request.json` (repo root, git-ignored — contains real member data, not committed). The file must have the shape described in `schemas/driving_plan_request.json`.

## 1. Direct algorithm test (no server needed)

Calls `calculate_driving_plan_logic` directly, prints the resulting plan and saves it to `driving_plan_<date>.json` at the repo root.

```bash
python backend/test/test_algorithm_realdata.py
```

## 2. Integration test (requires a running server)

Makes real HTTP requests against a running Flask instance.

```bash
# Terminal 1
cd backend
./start.sh

# Terminal 2
python backend/test/test_integration.py
```

This checks:
- `GET /api/v1/check` returns a healthy response.
- `POST /api/v1/drivingplan` returns a plan with the expected structure (day plans, parties with `driver`/`passengers`/`time`/`schoolbound`, correct types).

## 3. Ad-hoc WebUntis investigation scripts

`backend/test/test_full_term_scan.py` and `backend/test/test_only_base_timetable.py` are not part of routine testing — they're one-off scripts used to verify specific WebUntis behavior (full-term scheduling, `onlyBaseTimetable` semantics) against a live account. They require a stored credential:

```bash
python -c "import keyring; keyring.set_password('webuntis', '<initials>', '<password>')"
python backend/test/test_full_term_scan.py
```

## Manual testing with curl / Postman

```bash
curl http://localhost:1338/api/v1/check

curl -X POST http://localhost:1338/api/v1/drivingplan \
  -H "Content-Type: application/json" \
  -d @testdata/request.json
```

## Validation checklist

When checking a driving plan response by hand, verify:
- All 10 day plans are present (keys `"1"` through `"10"`).
- Each party has a `driver` (string) and `passengers` (array of strings).
- Times are integers in `HHMM` format.
- Each party has a `schoolbound` boolean.
- No member drives more than their configured max (see `MAX_DRIVES_FULLTIME` / `MAX_DRIVES_PARTTIME` in `backend/src/config.py`).
- Every active member is accounted for on each day (no one left behind).

## Common Issues

**Port already in use**
```bash
lsof -ti:1338 | xargs kill -9
```

**Module not found**
```bash
cd backend && pip install -r requirements.txt
```

**"Test data file not found"**
`testdata/request.json` is git-ignored and must be supplied locally — it isn't part of the repo.
