import json
from flask import Flask, jsonify, render_template
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('map.html')

@app.route('/earthquakes', methods=['GET'])
def get_earthquakes():
    # EMSC API endpoint
    url = "https://www.seismicportal.eu/fdsnws/event/1/query"
    params = {
        'format': 'json',
        'minlatitude': 39.5,  # Southern boundary of Albania
        'maxlatitude': 42.7,  # Northern boundary of Albania
        'minlongitude': 19.2,  # Western boundary of Albania
        'maxlongitude': 21.1,  # Eastern boundary of Albania
        'starttime': '2024-01-01',  # Example start time
        'endtime': '2024-12-31',   # Example end time
    }
    

    try:
        response = requests.get(url, params=params)
        print("Response Status Code:", response.status_code)  # Debugging
        print("Response Text:", response.text)               # Debugging
        response.raise_for_status()
        data = response.json()
        earthquakes = [
            {
                'latitude': feature['geometry']['coordinates'][1],
                'longitude': feature['geometry']['coordinates'][0],
                'magnitude': feature['properties']['mag'],
                'timestamp': feature['properties']['time']
            }
            for feature in data['features']
        ]
        return jsonify(earthquakes)
    except requests.RequestException as e:
        print("Error:", e)  # Debugging
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
