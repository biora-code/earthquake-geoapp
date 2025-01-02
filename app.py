import json
from flask import Flask, jsonify, render_template, request
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('map.html')

@app.route('/earthquakes', methods=['GET'])
def get_earthquakes():
    startdate = request.args.get('startdate', '2024-01-01')
    enddate = request.args.get('enddate', '2025-01-01')
    minmagnitude = float(request.args.get('minmagnitude', 0))

    # Fetch earthquake data from EMSC
    url = (
        f"https://www.seismicportal.eu/fdsnws/event/1/query?"
        f"format=json&minlatitude=39.5&maxlatitude=42.7&"
        f"minlongitude=19.2&maxlongitude=21.1&"
        f"starttime={startdate}&endtime={enddate}&minmagnitude={minmagnitude}"
    )

    try:
        response = requests.get(url)
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
    except Exception as e:
        return jsonify({'error': str(e)})


if __name__ == '__main__':
    app.run(debug=True)


