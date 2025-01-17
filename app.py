import json
import time
from flask import Flask, jsonify, render_template, request
import requests
from datetime import datetime

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

def predict_magnitude(fall_objects, vibration, description):
    """Simple rule-based magnitude prediction."""
    magnitude = 3.0  # Base magnitude

    if fall_objects == "yes" and vibration == "yes":
        magnitude = 5.0
    elif fall_objects == "yes":
        magnitude = 4.5
    elif vibration == "yes":
        magnitude = 4.0

    # Adjust magnitude based on keywords in description
    keywords = ["shaking", "rumbling", "cracks", "loud"]
    for keyword in keywords:
        if keyword in description.lower():
            magnitude += 0.1  # Fine-tune based on keyword presence

    return round(min(magnitude, 10.0), 1)  # Cap at 10.

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

@app.route('/report_earthquake')
def report_earthquake():
    return render_template('report_earthquake.html')



@app.route('/submit_report', methods=['POST'])
def submit_report():
    try:
        # Extract data from the form
        location = request.form.get('location')
        description = request.form.get('description')
        fall_objects = request.form.get('fall_objects') == "yes"
        vibration = request.form.get('vibration') == "yes"
        submission_time = datetime.utcnow().isoformat() + "Z"

        # Predict the magnitude
        predicted_magnitude = predict_magnitude(fall_objects, vibration, description)

        # Load existing reports
        reports = load_reports()

        # Add new report
        new_report = {
            "id": len(reports) + 1,
            "location": location,
            "description": description,
            "fall_objects": fall_objects,
            "vibration": vibration,
            "predicted_magnitude": predicted_magnitude,
            "submission_time": submission_time
        }
        reports.append(new_report)

        # Save back to JSON file
        save_reports(reports)

        # Return response
        return jsonify({
            "message": "Thank you for your report!",
            "predicted_magnitude": predicted_magnitude
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": "Failed to submit the report."}), 500



if __name__ == '__main__':
    app.run(debug=True)
