import json
import time
from flask import Flask, jsonify, render_template, request
import requests
from datetime import datetime
import numpy as np
from sklearn.ensemble import RandomForestRegressor


app = Flask(__name__)

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
'''
def predict_magnitude(shaking,duration, objects, reaction, damage):
    # Load dataset (simulated), BUT LATER ON WE HAVE TO SWITCH TO READING TO earthquake_reports and magnitude of a certain no of earthquakes nearby
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
    # Predict magnitude based on the input data
    input_data = np.array([[shaking, duration, objects, reaction, damage]])
    predicted_magnitude = model.predict(input_data)[0]
    return round(predicted_magnitude,2)
'''
def calculate_mmi(shaking, duration, objects, reactions, damage):
    """
    Calculates the Modified Mercalli Intensity (MMI) based on user responses.
    """
    mmi = (2 * shaking + duration + 1.5 * objects + reactions + 2 * damage) / 6
    return round(mmi, 1)

def estimate_magnitude(mmi):
    """
    Estimates earthquake magnitude from MMI using an empirical formula.
    """
    magnitude = 1.5 + 0.5 * mmi
    return round(magnitude, 1)

@app.route('/')
def home():
    return render_template('map.html')

def fetch_data_with_retry(url, max_retries=3, backoff_factor=2):
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

@app.route('/report_earthquake')
def report_earthquake():
    return render_template('report_earthquake.html')


@app.route('/submit_report', methods=['POST'])
def submit_report():
    try:
        # Extract data from the form
        location = request.form.get('location')
        shaking = int(request.form.get('shaking'))
        duration = int(request.form.get('duration'))
        objects = int(request.form.get('objects'))
        reactions = int(request.form.get('reactions'))
        damage = int(request.form.get('damage'))
        submission_time = datetime.utcnow().isoformat() + "Z"

        # Compute MMI and Magnitude
        mmi = calculate_mmi(shaking, duration, objects, reactions, damage)
        predicted_magnitude = estimate_magnitude(mmi)
        # Load existing reports
        reports = load_reports()

        # Add new report
        new_report = {
            "id": len(reports) + 1,
            "location": location,
            "shaking": shaking,
            "duration": duration,
            "objects": objects,
            "reactions": reactions,
            "damage": damage,
            "predicted_magnitude": predicted_magnitude,
            "submission_time": submission_time
        }
        reports.append(new_report)

        # Save back to JSON file
        save_reports(reports)

        # Return response
        return render_template('submit_report.html', predicted_magnitude=predicted_magnitude)


    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to submit the report."}), 500

if __name__ == '__main__':
    app.run(debug=True)