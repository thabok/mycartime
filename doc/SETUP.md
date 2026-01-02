# Carpool Time Backend - Setup and Usage Guide

## Overview

This backend service implements the core algorithm for calculating optimal carpool driving plans for teachers based on their schedules.

## Features

- **REST API** with Flask
- **WebUntis Integration** for timetable queries
- **Smart Algorithm** that:
  - Identifies mandatory drivers (unique time slots)
  - Creates driver candidate pools
  - Balances driving duties across members
  - Respects custom preferences and constraints
  - Minimizes passenger wait times
  - Optimizes for time convenience

## Installation

### Prerequisites

- Python 3.8 or higher
- pip

### Setup Steps

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure settings:**
   Edit `config.py` to set your WebUntis credentials and preferences:
   ```python
   WEBUNTIS_SERVER = "your-server.webuntis.com"
   WEBUNTIS_SCHOOL = "your-school-name"
   TIME_TOLERANCE_MINUTES = 30
   ```

## Running the Service

### Start the server:
```bash
python app.py
```

The service will start on `http://localhost:1338`

### Test the algorithm:
```bash
python test_algorithm.py
```

This will run the algorithm with sample data and save output to `test_driving_plan_output.json`

## API Endpoints

### Health Check
```
GET /api/v1/check
```

**Response:**
```json
true
```

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

## Algorithm Details

### Driver Candidate Pools

The algorithm groups members by their arrival/departure times (within tolerance) and creates "driver pools":

1. **Mandatory Drivers (Pool Size = 1)**: Members who must drive because no one else shares their time slot
2. **Flexible Pools (Pool Size > 1)**: Multiple members available, algorithm selects optimal driver(s)

### Selection Criteria

When choosing drivers from flexible pools:
- Prioritize members with fewer drives
- Balance load across full-time (max 4 drives) and part-time (max 2 drives) members
- Consider car capacity
- Respect custom preferences (needsCar, drivingSkip, etc.)

### Time Handling

- **Tolerance**: Default 30 minutes to group similar times
- **Party Time**: 
  - Schoolbound: Earliest time of all members
  - Homebound: Latest time of all members

### Custom Day Settings

Members can override their schedule for any day:
- `ignoreCompletely`: Skip this member entirely
- `needsCar`: Member must drive (cannot be passenger)
- `drivingSkip`: Member cannot drive (can only be passenger)
- `skipMorning/Afternoon`: Skip one direction
- `customStart/End`: Override times (HH:MM format)

## Architecture

```
backend/
├── app.py                    # Flask application & API endpoints
├── models.py                 # Data models (Member, Party, DayPlan, etc.)
├── algorithm_service.py      # Core driving plan algorithm
├── timetable_service.py      # WebUntis connector
├── utils.py                  # Utility functions
├── config.py                 # Configuration
├── requirements.txt          # Dependencies
└── test_algorithm.py         # Test script
```

## Troubleshooting

### WebUntis Connection Issues

If WebUntis connection fails, the service falls back to mock timetables based on custom day settings and default times (7:55 AM - 3:30 PM).

To fix:
1. Verify `config.py` has correct server and school name
2. Check credentials are valid
3. Ensure network access to WebUntis server

### Algorithm Not Finding Solutions

If the algorithm cannot create a valid plan:
1. Check that enough members have cars
2. Verify custom day settings aren't too restrictive
3. Increase `TIME_TOLERANCE_MINUTES` in config.py
4. Check logs for specific errors

### Port Already in Use

If port 1338 is busy:
```bash
# Kill existing process
lsof -ti:1338 | xargs kill -9

# Or change port in config.py
PORT = 1339
```

## Development

### Adding New Features

1. **Models**: Add new data classes in `models.py`
2. **Algorithm Logic**: Extend `algorithm_service.py`
3. **API Endpoints**: Add routes in `app.py`
4. **Utils**: Add helper functions in `utils.py`

### Testing

Run the test script after changes:
```bash
python test_algorithm.py
```

Check the output JSON matches the schema in `../schemas/driving_plan_new.json`

## License

See LICENSE file in project root.
