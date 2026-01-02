# Quick Testing Guide

## Start the Server

```bash
cd backend
python app.py
```

Server will run on `http://localhost:1338`

## Test Endpoints

### 1. Health Check
```bash
curl http://localhost:1338/api/v1/check
```

Expected response: `true`

### 2. Calculate Driving Plan

Using the example request file:
```bash
curl -X POST http://localhost:1338/api/v1/drivingplan \
  -H "Content-Type: application/json" \
  -d @example_request.json
```

Or with inline data:
```bash
curl -X POST http://localhost:1338/api/v1/drivingplan \
  -H "Content-Type: application/json" \
  -d '{
    "persons": [
      {
        "firstName": "John",
        "lastName": "Doe",
        "initials": "Jd",
        "numberOfSeats": 5,
        "isPartTime": false,
        "customDays": {}
      }
    ],
    "scheduleReferenceStartDate": "20251223",
    "username": "test",
    "hash": "test123"
  }'
```

### 3. Run Test Script

```bash
cd backend
python test_algorithm.py
```

This will:
- Load sample members
- Create mock timetables
- Run the algorithm
- Print detailed output
- Save result to `test_driving_plan_output.json`

### 4. Run Integration Test

**Prerequisites:** The Flask server must be running.

```bash
# Terminal 1: Start the server
cd backend
python app.py

# Terminal 2: Run integration test
cd backend
python test_integration.py
```

This integration test will:
- Load real test data from `testdata/request.json`
- Make actual HTTP requests to the running service
- Test the health check endpoint
- Test the driving plan calculation endpoint with full validation
- Verify response structure and data types
- Print detailed test results

The test uses the actual request data with 17 members and realistic custom day configurations.

## Using Postman or Similar Tools

1. **Import the example request**
   - Method: POST
   - URL: `http://localhost:1338/api/v1/drivingplan`
   - Headers: `Content-Type: application/json`
   - Body: Copy content from `example_request.json`

2. **Send request**

3. **Verify response**
   - Should have `summary` field
   - Should have `dayPlans` object with keys "1" through "10"
   - Each day plan should have `parties` array
   - Each party should have `driver`, `time`, `passengers`, `schoolbound`

## Common Issues

### Port already in use
```bash
lsof -ti:1338 | xargs kill -9
```

### Module not found
```bash
pip install -r requirements.txt
```

### Import errors
Make sure you're in the `backend` directory:
```bash
cd /Users/thabok/Documents/GitHub/mycartime/backend
python app.py
```

## Expected Output Format

```json
{
  "summary": "- Jonas (Ot): 4\n- Felix (Nl): 4\n...",
  "dayPlans": {
    "1": {
      "dayOfWeekABCombo": {
        "dayOfWeek": "MONDAY",
        "isWeekA": true,
        "uniqueNumber": 1
      },
      "parties": [
        {
          "dayOfWeekABCombo": {...},
          "driver": "Li",
          "time": 755,
          "passengers": ["Ki", "Wr"],
          "isDesignatedDriver": false,
          "drivesDespiteCustomPrefs": false,
          "schoolbound": true
        }
      ],
      "schoolboundTimesByInitials": {
        "Li": 755,
        "Ki": 755
      },
      "homeboundTimesByInitials": {
        "Li": 1530,
        "Ki": 1530
      }
    }
  }
}
```

## Validation

Check that the output:
- ✅ Has all 10 day plans (keys "1" through "10")
- ✅ Each party has a driver (string)
- ✅ Passengers are array of strings
- ✅ Times are in HHMM format (integers)
- ✅ Each party has `schoolbound` boolean
- ✅ No member drives more than their max (4 full-time, 2 part-time)
- ✅ All members are accounted for each day

## Logs

Check console output for detailed logs:
- Connection status
- Algorithm progress
- Driver pool information
- Party creation details
- Any errors or warnings
