# app.py

import os
import base64
import json
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

# Configure Flask app
app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing

# --- Gemini API Configuration ---
# It's recommended to use environment variables for your API key
GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', 'AIzaSyAM9kPnDMD0ZtJf564s6VtbyGs4C2Iw8VY') # Replace with your key if not using env vars
genai.configure(api_key=GOOGLE_API_KEY)
# --- End of Gemini API Configuration ---

# Set up the Generative Model
model = genai.GenerativeModel('gemini-1.5-flash') # Using the latest recommended model

@app.route('/scan_celestial_body', methods=['POST'])
def scan_celestial_body():
    """
    Handles the image analysis and returns a list of identified celestial bodies.
    """
    try:
        print("HITEDDDDDDD 1")
        data = request.json
        if not data or 'imageData' not in data:
            return jsonify({"error": "No image data provided"}), 400

        image_data = data['imageData']
        image_bytes = base64.b64decode(image_data)

        image_part = {
            "mime_type": "image/jpeg",
            "data": image_bytes
        }

        prompt_text = (
            "Analyze this textbook page image. Identify any celestial bodies, "
            "such as planets, stars, or galaxies, **based solely on the images shown**. "
            "Ignore any text descriptions. If multiple are found, return their names "
            "as a comma-separated list. If none are found, return the exact phrase "
            "'No celestial bodies identified'. Return only the names and nothing else."
        )

        response = model.generate_content([prompt_text, image_part])
        
        # Process the response to be a clean list
        result_text = response.text.strip()
        if result_text == "No celestial bodies identified":
            celestial_bodies = []
        else:
            # Split by comma and strip any extra whitespace from each name
            celestial_bodies = [name.strip() for name in result_text.split(',')]

        return jsonify({"celestial_bodies": celestial_bodies})

    except Exception as e:
        print(f"An error occurred in /scan_celestial_body: {e}")
        return jsonify({"error": "An internal server error occurred."}), 500

@app.route('/get_planet_details', methods=['POST'])
def get_planet_details():
    """
    Fetches specific details for a given celestial body.
    """
    try:
        print("HITEDDDDDDD 2")
        data = request.json
        planet_name = data.get('planet_name')

        if not planet_name:
            return jsonify({"error": "No planet name provided"}), 400

        # A more structured prompt to get data for Unity AR
        prompt = f"""
        You are an astronomy data assistant. Your task is to provide specific information 
        about a celestial body in a clean JSON format.

        For the celestial body "{planet_name}", provide the following details:
        1. A concise, one-paragraph summary suitable for a student.
        2. The mass in kilograms (as a string, e.g., "5.972e24").
        3. The mean radius in kilometers (as a string, e.g., "6371").
        4. The direction of axial rotation (the answer should be either "West to East" or "East to West").

        Return ONLY a single valid JSON object with the following keys: "name", "summary", "mass_kg", "radius_km", "rotation_direction". 
        Do not include markdown formatting or any other text.
        """
        
        response = model.generate_content(prompt)
        
        # Clean the response and parse the JSON
        # The model might wrap the JSON in ```json ... ```, so we strip it.
        cleaned_response = response.text.strip().replace('```json', '').replace('```', '')
        details = json.loads(cleaned_response)

        return jsonify(details)

    except Exception as e:
        print(f"An error occurred in /get_planet_details: {e}")
        return jsonify({"error": "An internal server error occurred while fetching details."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)