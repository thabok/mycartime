"""
Test script for algorithm with real request data.
Loads data from testdata/request.json and calls the algorithm directly.
"""
import base64
import json
import sys
from pathlib import Path

# Add backend/src directory to path so all imports work
backend_src = Path(__file__).parent.parent / 'src'
sys.path.insert(0, str(backend_src))

from app import calculate_driving_plan_logic  # type: ignore


def main():
    # Load request data
    request_file = Path(__file__).parent.parent.parent / 'testdata' / 'request.json'
    
    print(f"Loading request data from: {request_file}")
    with open(request_file, 'r') as f:
        data = json.load(f)
    
    # Extract parameters
    persons_data = data['persons']
    start_date_str = data['scheduleReferenceStartDate']
    username = data['username']
    password = base64.b64decode(data['hash']).decode('utf-8')
    
    print(f"\nCalculating driving plan for {len(persons_data)} members")
    print(f"Start date: {start_date_str}")
    print(f"Username: {username}")
    print()
    
    # Call the algorithm
    try:
        driving_plan = calculate_driving_plan_logic(
            persons_data=persons_data,
            start_date_str=start_date_str,
            username=username,
            password=password
        )
        print("✅ Driving plan calculated successfully.")

        # Convert to dict for JSON serialization
        driving_plan_dict = driving_plan.to_dict()
        print(json.dumps(driving_plan_dict, indent=2))

        # Save to file
        output_file = Path(__file__).parent.parent.parent / f'driving_plan_{start_date_str}.json'
        with open(output_file, 'w') as f:
            json.dump(driving_plan_dict, f, indent=2)
        print(f"\n💾 Saved to: {output_file}")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
