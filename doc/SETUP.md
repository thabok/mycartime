# Carpool Time Backend - Setup and Usage Guide

## Overview

This backend service implements the core algorithm for calculating optimal carpool driving plans for teachers based on their schedules. See [internal_doc.md](internal_doc.md) for the full functional spec.

## Installation

### Prerequisites

- Python 3.9+
- pip

### Setup Steps

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   Note: `webuntis` is installed from a local fork (see `../webuntis`), not from PyPI, so it is intentionally not listed in `requirements.txt`.

4. **Configure settings:**
   Edit `backend/src/config.py` to set your WebUntis server/school and algorithm parameters:
   ```python
   WEBUNTIS_SERVER = "https://your-school.webuntis.com"
   WEBUNTIS_SCHOOL = "your-school-name"
   TIME_TOLERANCE_MINUTES = 30
   ```

## Running the Service

```bash
cd backend
./start.sh
```

`start.sh` creates/activates the virtualenv, installs dependencies, and starts the server via `python -m src.app`. The service starts on `http://localhost:1338` (configurable via `PORT` in `config.py`).

## API Endpoints

### Health Check
```
GET /api/v1/check
```
**Response:** `true`

### Suggested Reference Date
```
POST /api/v1/suggestedreferencedate
Content-Type: application/json
```
**Request Body:**
```json
{
  "username": "your_username",
  "hash": "base64_encoded_password"
}
```
**Response:**
```json
{ "referenceDate": "20251223" }
```
Returns the next date (today included) that falls in an "A" week, based on the school's own week numbering. If WebUntis can't be reached, returns an error; the frontend should fail silently and let the user pick a date manually.

### Calculate Driving Plan
```
POST /api/v1/drivingplan
Content-Type: application/json
```

**Request Body:**
```json
{
  "persons": [
    {
      "firstName": "John",
      "lastName": "Doe",
      "initials": "Jd",
      "numberOfSeats": 5,
      "isPartTime": false,
      "customDays": {
        "0": {
          "ignoreCompletely": false,
          "noWaitingAfternoon": false,
          "needsCar": false,
          "drivingSkip": false,
          "skipMorning": false,
          "skipAfternoon": false,
          "customStart": "",
          "customEnd": ""
        }
      }
    }
  ],
  "scheduleReferenceStartDate": "20251223",
  "username": "your_username",
  "hash": "base64_encoded_password"
}
```
`scheduleReferenceStartDate` accepts either a `YYYYMMDD` string or integer.

**Response:**
```json
{
  "summary": "- John (Jd): 4\n",
  "dayPlans": {
    "1": {
      "dayOfWeekABCombo": {
        "dayOfWeek": "MONDAY",
        "isWeekA": true,
        "uniqueNumber": 1
      },
      "parties": [...],
      "schoolboundTimesByInitials": {...},
      "homeboundTimesByInitials": {...}
    }
  }
}
```

Request/response shapes are formally defined in `schemas/driving_plan_request.json` and `schemas/driving_plan.json`.

## Algorithm Details

See [internal_doc.md](internal_doc.md#algorithm) for the full algorithm spec, including the 5-phase implementation and custom day preference rules.

Key configuration (`backend/src/config.py`):
- `TIME_TOLERANCE_MINUTES` (default 30): max deviation in minutes to group members into the same time slot.
- `EXACT_MATCH_TOLERANCE_MINUTES` (default 5): deviation still treated as an "exact" match, e.g. for grouping passengers with an identical schedule.
- `MAX_DRIVES_FULLTIME` (default 4) / `MAX_DRIVES_PARTTIME` (default 3): max drives per member type over the 2-week cycle.

If the WebUntis connection fails, the service falls back to mock timetables based on custom day settings and default times (7:55 AM - 3:30 PM).

## Architecture

```
backend/
├── src/
│   ├── app.py                 # Flask application & API endpoints
│   ├── models.py               # Data models (Member, Party, DayPlan, etc.)
│   ├── algorithm_service.py    # Core driving plan algorithm
│   ├── timetable_service.py    # WebUntis connector
│   ├── utils.py                 # Utility functions
│   └── config.py                # Configuration
├── test/                        # Test & investigation scripts (see TESTING.md)
├── requirements.txt
└── start.sh                     # Setup + start script
```

## Troubleshooting

### WebUntis Connection Issues

1. Verify `config.py` has the correct server and school name.
2. Check credentials are valid.
3. Ensure network access to the WebUntis server.

### Algorithm Not Finding Solutions

1. Check that enough members have cars.
2. Verify custom day settings aren't too restrictive.
3. Increase `TIME_TOLERANCE_MINUTES` in `config.py`.
4. Check logs for specific errors.

### Port Already in Use

```bash
lsof -ti:1338 | xargs kill -9
```
Or change `PORT` in `config.py`.
