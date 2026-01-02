# Date Format Update: YYMMDD → YYYYMMDD

## Summary

Updated the date format for `scheduleReferenceStartDate` from 2-digit year (YYMMDD) to 4-digit year (YYYYMMDD) format across the entire codebase.

### Reason for Change
- Better clarity and consistency with ISO 8601 standards
- Avoids ambiguity with century determination
- More explicit and less error-prone

### Format Change
- **Old Format**: YYMMDD (e.g., `"251223"` for December 23, 2025)
- **New Format**: YYYYMMDD (e.g., `"20251223"` for December 23, 2025)

## Files Modified

### 1. Schema Files

**`schemas/driving_plan_request.json`**
- Updated `scheduleReferenceStartDate` to accept both string and integer
- String pattern: `^[0-9]{8}$` (8 digits)
- Integer range: 19000101 to 21001231
- Updated description to reflect YYYYMMDD format

### 2. Backend Implementation

**`backend/utils.py`**
- Updated `parse_date_yymmdd()` function
  - Changed format string from `"%y%m%d"` to `"%Y%m%d"`
  - Updated docstring to reflect YYYYMMDD format
  - Updated example from `"251223"` to `"20251223"`

**`backend/app.py`**
- Updated date parsing to handle both integer and string input
  - Added conversion: `if isinstance(date_value, int): date_value = str(date_value)`
- Updated error message: "Expected YYYYMMDD" (was "Expected YYMMDD")
- Updated docstring example from `"251223"` to `"20251223"`

**`backend/test_algorithm.py`**
- Updated test date from `"251223"` to `"20251223"`

**`backend/example_request.json`**
- Updated `scheduleReferenceStartDate` from `"251223"` to `"20251223"`

### 3. Documentation Files

**`backend/TESTING.md`**
- Updated curl example from `"251223"` to `"20251223"`

**`backend/SETUP.md`**
- Updated example request from `"251223"` to `"20251223"`

**`backend/IMPLEMENTATION_SUMMARY.md`**
- Updated format reference from "YYMMDD format" to "YYYYMMDD format"
- Updated example from `"251223"` to `"20251223"`

### 4. Test Data (No Change Needed)

**`testdata/request.json`**
- Already uses correct format: `20251103` (integer)
- Backend now handles both integer and string formats

## Backward Compatibility

⚠️ **Breaking Change**: This is a breaking change for any existing clients or stored data using the old YYMMDD format.

### Migration Guide for Clients

If you have existing code using the old format, update as follows:

**Before:**
```json
{
  "scheduleReferenceStartDate": "251223"
}
```

**After:**
```json
{
  "scheduleReferenceStartDate": "20251223"
}
```

Or as integer:
```json
{
  "scheduleReferenceStartDate": 20251223
}
```

## Testing

The implementation now accepts both formats:
- String: `"20251223"`
- Integer: `20251223`

Both will be correctly parsed to December 23, 2025.

### Test Examples

```bash
# String format
curl -X POST http://localhost:1338/api/v1/drivingplan \
  -H "Content-Type: application/json" \
  -d '{"scheduleReferenceStartDate": "20251223", ...}'

# Integer format (will be auto-converted)
curl -X POST http://localhost:1338/api/v1/drivingplan \
  -H "Content-Type: application/json" \
  -d '{"scheduleReferenceStartDate": 20251223, ...}'
```

## Validation

✅ Python parsing updated to use 4-digit year format (`%Y%m%d`)  
✅ JSON schema accepts both string and integer  
✅ Backend handles automatic integer-to-string conversion  
✅ All documentation examples updated  
✅ Test files updated  
✅ Error messages reflect new format  

## Date Format Details

The new YYYYMMDD format:
- Year: 4 digits (e.g., 2025)
- Month: 2 digits, zero-padded (01-12)
- Day: 2 digits, zero-padded (01-31)

Examples:
- January 1, 2025: `20250101`
- December 31, 2025: `20251231`
- February 5, 2026: `20260205`
