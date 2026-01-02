# Integration Test

This integration test makes actual HTTP requests to the running Flask service using real test data from `testdata/request.json`.

## Prerequisites

1. Install dependencies (including `requests`):
   ```bash
   pip install -r requirements.txt
   ```

2. Start the Flask server:
   ```bash
   python backend/app.py
   ```
   
   The server should be running on `http://localhost:1338`

## Running the Test

In a separate terminal:

```bash
cd backend
python test_integration.py
```

## What It Tests

1. **Health Check Endpoint** (`GET /api/v1/check`)
   - Verifies the service is running
   - Checks for proper response format

2. **Driving Plan Calculation** (`POST /api/v1/drivingplan`)
   - Loads test data from `testdata/request.json` (17 members)
   - Posts to the service endpoint
   - Validates response structure:
     - Presence of `dayPlans` field
     - Correct structure for each day plan
     - Proper data types (driver as string, time as int, etc.)
     - Required fields (driver, passengers, time, schoolbound)
   - Reports total number of parties created
   - Shows sample party details

## Expected Output

```
============================================================
Starting Integration Tests
============================================================
Target URL: http://localhost:1338
Test data: /Users/thabok/Documents/GitHub/mycartime/testdata/request.json

2025-12-30 10:30:00 - INFO - Loading test data from: .../testdata/request.json
2025-12-30 10:30:00 - INFO - Loaded test data with 17 persons
2025-12-30 10:30:00 - INFO - Testing health check endpoint...
2025-12-30 10:30:00 - INFO - ✓ Health check passed

2025-12-30 10:30:01 - INFO - Testing driving plan calculation endpoint...
2025-12-30 10:30:05 - INFO - Received driving plan with 10 day plans
2025-12-30 10:30:05 - INFO -   Day 1: 8 parties
2025-12-30 10:30:05 - INFO -   Day 2: 8 parties
...
2025-12-30 10:30:05 - INFO - ✓ Driving plan calculation passed
2025-12-30 10:30:05 - INFO -   Total parties across all days: 80
2025-12-30 10:30:05 - INFO -   Sample party: Driver=Li, Passengers=Ki,Wr, Time=755, Schoolbound=True

============================================================
Test Results Summary
============================================================
✓ PASS: Health Check
✓ PASS: Calculate Driving Plan
============================================================
All tests passed! 🎉
```

## Troubleshooting

### "Could not connect to server"
- Make sure the Flask server is running on port 1338
- Check for port conflicts: `lsof -i :1338`

### "Test data file not found"
- Ensure you're running from the correct directory
- The script looks for `testdata/request.json` relative to the repo root

### HTTP Errors
- Check server logs for error details
- Verify the test data format matches expected schema
- Ensure all dependencies are installed

## Test Data

The test uses `testdata/request.json` which contains:
- 17 real carpool members with various configurations
- Custom day settings (different start/end times, skip days, etc.)
- Mix of full-time and part-time members
- Reference start date: November 3, 2025 (20251103)

This provides a realistic test scenario for the driving plan algorithm.
