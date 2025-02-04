import json
import time
from flask import Flask, jsonify, render_template, request
import requests
from datetime import datetime
import numpy as np
from sklearn.ensemble import RandomForestRegressor

app = Flask(__name__)




@app.route('/')
def home():
    return render_template('map.html')

def fetch_data_with_retry(url, max_retries=3, backoff_factor=2):
    """
    Fetch data from the given URL with retry on rate limiting.
    """
    retries = 0
    headers = {'User-Agent': 'MyFlaskApp/1.0'}
    
    while retries < max_retries:
        try:
            response = requests.get(url, headers=headers)
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Content: {response.text}")
            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After",2))  
                print(f"Rate limited. Retrying after {retry_after} seconds...")
                time.sleep(retry_after)
                retries += 1
                continue

            response.raise_for_status()
            return response.json()  

        except requests.exceptions.RequestException as e:
            print(f"Error: {e}")
            retries += 1
            time.sleep(backoff_factor ** retries)  

    raise Exception("Max retries exceeded. Could not fetch data.")

@app.route('/earthquakes', methods=['GET'])
def get_earthquakes():
    startdate = request.args.get('startdate', '2024-01-01')
    enddate = request.args.get('enddate', '2025-12-31')
    minmagnitude = float(request.args.get('minmagnitude', 3))

    # Construct the API URL
    url = (
        f"https://www.seismicportal.eu/fdsnws/event/1/query?"
        f"format=json&minlatitude=39.5&maxlatitude=42.7&"
        f"minlongitude=19.2&maxlongitude=21.1&"
        f"starttime={startdate}&endtime={enddate}&minmagnitude={minmagnitude}"
    )

    try:
        response = requests.get(url)
        print(f"Response Status Code: {response.status_code}")

        # Check for no content (204)
        if response.status_code == 204:
            return jsonify({'error': 'No earthquake data available for the specified filters.'}), 204

        response.raise_for_status()  # Raise exception for HTTP errors
        data = response.json()  # Parse JSON

        # Extract relevant earthquake data
        earthquakes = [
            {
                'latitude': feature['geometry']['coordinates'][1],
                'longitude': feature['geometry']['coordinates'][0],
                'magnitude': feature['properties']['mag'],
                'timestamp': feature['properties']['time'],
                'depth': feature['properties']['depth']
            }
            for feature in data.get('features', [])
        ]

        print(f"Filtered Earthquakes: {len(earthquakes)} returned.")
        return jsonify(earthquakes)

    except requests.exceptions.RequestException as e:
        print(f"Error fetching earthquake data: {e}")
        return jsonify({'error': 'Failed to fetch data from the seismic database.'}), 500

# File to store reports
FILE_PATH = "earthquake_reports.json"

def load_reports():
    """Load existing earthquake reports from JSON file."""
    try:
        with open(FILE_PATH, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return []  # Return empty list if file doesn't exist

def save_reports(reports):
    """Save reports to JSON file."""
    with open(FILE_PATH, "w") as file:
        json.dump(reports, file, indent=4)
# Load dataset (simulated)
report_data = {
    "shaking": [1, 2, 3, 4, 5, 5, 3, 4, 2, 1],
    "duration": [1, 2, 3, 4, 4, 3, 2, 2, 1, 1],
    "objects": [1, 2, 3, 4, 5, 4, 3, 3, 2, 1],
    "reaction": [1, 2, 3, 4, 5, 5, 4, 3, 2, 1],
    "damage": [1, 2, 3, 4, 5, 5, 3, 2, 2, 1],
    "magnitude": [3.1, 3.5, 4.2, 5.0, 6.8, 7.1, 4.5, 5.5, 3.8, 3.0]
}

X = np.column_stack((report_data["shaking"], report_data["duration"], report_data["objects"], report_data['reaction'], report_data["damage"]))
y = np.array(report_data["magnitude"])

# Train the model
model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X, y)

@app.route("/report_earthquake", methods=["POST"])
def report_earthquake():
    # Make sure the data is coming in JSON format
    if request.is_json:
        report_data = request.get_json()
        
        # Extract values from the request data
        shaking = report_data.get("shaking")
        duration = report_data.get("duration")
        objects = report_data.get("objects")
        reaction = report_data.get("reaction")
        damage = report_data.get("damage")

        # Check if all required fields are provided
        if None in [shaking, duration, objects, reaction, damage]:
            return jsonify({"error": "Missing input fields"}), 400
        
        # Predict magnitude based on the input data
        input_data = np.array([[shaking, duration, objects, reaction, damage]])
        predicted_magnitude = model.predict(input_data)[0]

        # Create report dictionary
        report = {
            "shaking": shaking,
            "duration": duration,
            "objects": objects,
            "reaction": reaction,
            "damage": damage,
            "predicted_magnitude": round(predicted_magnitude, 1)
        }

        # Save the report to the JSON file
        reports = load_reports()
        reports.append(report)
        save_reports(reports)
        
        # Return success message
        return jsonify({"message": "Report saved", "predicted_magnitude": report["predicted_magnitude"]})

    # If the request is not in JSON format, return an error
    return jsonify({"error": "Invalid content type. Expecting JSON data."}), 400



@app.route("/reports", methods=["GET"])
def get_reports():
    """Retrieve all saved earthquake reports."""
    return jsonify(load_reports())


if __name__ == '__main__':
    app.run(debug=True)
