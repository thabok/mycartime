"""
Integration test for the Carpool Time backend service.
This test makes actual HTTP requests to the running Flask service.

Prerequisites:
- The Flask service must be running (python backend/app.py)
- The service should be accessible at http://localhost:1338

Usage:
    python backend/test_integration.py
"""
import json
import logging
import sys
from pathlib import Path

import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
BASE_URL = "http://localhost:1338"
TESTDATA_PATH = Path(__file__).parent.parent / "testdata" / "request.json"


def load_test_data():
    """Load test data from testdata/request.json"""
    logger.info(f"Loading test data from: {TESTDATA_PATH}")
    
    if not TESTDATA_PATH.exists():
        logger.error(f"Test data file not found: {TESTDATA_PATH}")
        sys.exit(1)
    
    with open(TESTDATA_PATH, 'r') as f:
        data = json.load(f)
    
    logger.info(f"Loaded test data with {len(data.get('persons', []))} persons")
    return data


def test_health_check():
    """Test the health check endpoint"""
    logger.info("Testing health check endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/v1/check", timeout=5)
        response.raise_for_status()
        
        result = response.json()
        assert result is True, f"Expected True, got {result}"
        
        logger.info("✓ Health check passed")
        return True
    except requests.exceptions.ConnectionError:
        logger.error("✗ Could not connect to server. Is it running?")
        return False
    except Exception as e:
        logger.error(f"✗ Health check failed: {e}")
        return False


def test_calculate_drivingplan(test_data):
    """Test the driving plan calculation endpoint"""
    logger.info("Testing driving plan calculation endpoint...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/v1/drivingplan",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Validate response structure
        assert "dayPlans" in result, "Response missing 'dayPlans' field"
        day_plans = result["dayPlans"]
        
        logger.info(f"Received driving plan with {len(day_plans)} day plans")
        
        # Validate each day plan
        total_parties = 0
        for day_num, day_plan in day_plans.items():
            assert "parties" in day_plan, f"Day {day_num} missing 'parties' field"
            parties = day_plan["parties"]
            total_parties += len(parties)
            
            logger.info(f"  Day {day_num}: {len(parties)} parties")
            
            # Validate each party
            for i, party in enumerate(parties):
                assert "driver" in party, f"Day {day_num}, Party {i}: missing 'driver'"
                assert "passengers" in party, f"Day {day_num}, Party {i}: missing 'passengers'"
                assert "time" in party, f"Day {day_num}, Party {i}: missing 'time'"
                assert "schoolbound" in party, f"Day {day_num}, Party {i}: missing 'schoolbound'"
                
                # Validate types
                assert isinstance(party["driver"], str), f"Driver should be string (initials)"
                assert isinstance(party["passengers"], str), f"Passengers should be string"
                assert isinstance(party["time"], int), f"Time should be integer (HHMM format)"
                assert isinstance(party["schoolbound"], bool), f"Schoolbound should be boolean"
        
        logger.info(f"✓ Driving plan calculation passed")
        logger.info(f"  Total parties across all days: {total_parties}")
        
        # Print sample party details
        if day_plans:
            first_day = next(iter(day_plans.keys()))
            first_day_parties = day_plans[first_day]["parties"]
            if first_day_parties:
                sample_party = first_day_parties[0]
                logger.info(f"  Sample party: Driver={sample_party['driver']}, "
                          f"Passengers={sample_party['passengers']}, "
                          f"Time={sample_party['time']}, "
                          f"Schoolbound={sample_party['schoolbound']}")
        
        return True
    except requests.exceptions.ConnectionError:
        logger.error("✗ Could not connect to server. Is it running?")
        return False
    except requests.exceptions.HTTPError as e:
        logger.error(f"✗ HTTP error: {e}")
        if hasattr(e.response, 'text'):
            logger.error(f"  Response: {e.response.text}")
        return False
    except AssertionError as e:
        logger.error(f"✗ Validation failed: {e}")
        return False
    except Exception as e:
        logger.error(f"✗ Driving plan calculation failed: {e}")
        return False


def save_result(result, output_path="test_integration_output.json"):
    """Save the result to a file for inspection"""
    output_file = Path(__file__).parent / output_path
    with open(output_file, 'w') as f:
        json.dump(result, f, indent=2)
    logger.info(f"Result saved to: {output_file}")


def run_tests():
    """Run all integration tests"""
    logger.info("=" * 60)
    logger.info("Starting Integration Tests")
    logger.info("=" * 60)
    logger.info(f"Target URL: {BASE_URL}")
    logger.info(f"Test data: {TESTDATA_PATH}")
    logger.info("")
    
    # Load test data
    test_data = load_test_data()
    
    # Run tests
    results = []
    
    # Test 1: Health check
    results.append(("Health Check", test_health_check()))
    logger.info("")
    
    # Test 2: Calculate driving plan
    if results[0][1]:  # Only run if health check passed
        results.append(("Calculate Driving Plan", test_calculate_drivingplan(test_data)))
    else:
        logger.warning("Skipping driving plan test due to failed health check")
        results.append(("Calculate Driving Plan", False))
    
    logger.info("")
    logger.info("=" * 60)
    logger.info("Test Results Summary")
    logger.info("=" * 60)
    
    all_passed = True
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{status}: {test_name}")
        if not passed:
            all_passed = False
    
    logger.info("=" * 60)
    
    if all_passed:
        logger.info("All tests passed! 🎉")
        sys.exit(0)
    else:
        logger.error("Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
