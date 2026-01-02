# Carpool Time Backend Service

This is the backend service for the Carpool Time application that calculates optimal driving plans for teachers.

## Installation

```bash
pip install -r requirements.txt
```

## Running the Service

```bash
python app.py
```

The service will start on port 1338.

## API Endpoints

- `GET /api/v1/check` - Health check endpoint
- `POST /api/v1/drivingplan` - Calculate driving plan

## Architecture

- `app.py` - Flask application entry point
- `models/` - Data models (Member, Party, DayPlan, etc.)
- `services/` - Business logic services
  - `timetable_service.py` - Timetable provider connector
  - `algorithm_service.py` - Core driving plan algorithm
- `utils/` - Utility functions
