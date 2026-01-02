import json

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

#
# Driving Plan Calculation
#
@app.route('/api/v1/drivingplan', methods=['POST'])
def calculate_drivingplan():
    try:
        with open('testdata/driving-plan.json', 'r') as f:
            plan = json.load(f)
        return jsonify(plan['data']), 200
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

#
# Status check
#
@app.route('/api/v1/check', methods=['GET'])
def check():
    print(f"Received health check request from {request.remote_addr}")
    return jsonify(True)

if __name__ == '__main__':
    app.run(debug=True, port=1338)
