# ui.py

import streamlit as st
import requests
import base64

# --- Page Configuration ---
st.set_page_config(layout="wide", page_title="Celestial Body Scanner")

# --- Initialize Session State ---
# This helps the app remember variables across reruns
if 'scan_complete' not in st.session_state:
    st.session_state.scan_complete = False
if 'celestial_bodies' not in st.session_state:
    st.session_state.celestial_bodies = []
if 'planet_details' not in st.session_state:
    st.session_state.planet_details = None

# --- Callback Function to Reset State ---
# This function is called whenever a new image is uploaded or taken,
# ensuring the app is ready for a new scan.
def reset_scan():
    st.session_state.scan_complete = False
    st.session_state.celestial_bodies = []
    st.session_state.planet_details = None

# --- UI elements ---
st.title("🪐 Celestial Body Scanner")
st.markdown("Use your camera or upload a photo of a textbook page. I'll identify the celestial bodies, and then you can select one to learn more about it!")

# Define the API endpoints
API_URL_SCAN = "http://192.168.0.144:5000/scan_celestial_body"
API_URL_DETAILS = "http://192.168.0.144:5000/get_planet_details"

# --- NEW: Image Input with Tabs ---
tab1, tab2 = st.tabs(["📁 Upload a Photo", "📸 Use Camera"])

with tab1:
    uploaded_image = st.file_uploader(
        "Select a photo from your device",
        type=["png", "jpg", "jpeg"],
        on_change=reset_scan # Reset state when a new file is chosen
    )

with tab2:
    camera_image = st.camera_input(
        "Take a photo with your camera",
        on_change=reset_scan # Reset state when a new photo is taken
    )

# Consolidate the image input source
image_input = uploaded_image or camera_image

# --- Process the Image ---
if image_input and not st.session_state.scan_complete:
    with st.spinner("Scanning for celestial bodies... 🔭"):
        try:
            # .getvalue() works for both UploadedFile and CameraInput
            image_bytes = image_input.getvalue()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')

            payload = {"imageData": base64_image}
            response = requests.post(API_URL_SCAN, json=payload, timeout=30)

            if response.status_code == 200:
                st.session_state.celestial_bodies = response.json().get("celestial_bodies", [])
                st.session_state.scan_complete = True
                st.rerun()
            else:
                st.error(f"API Error ({response.status_code}): {response.json().get('error')}")

        except requests.exceptions.ConnectionError:
            st.error("Connection Error: Could not connect to the API server. Is the Flask app running?")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")

# --- Display Results and Fetch Details ---
if st.session_state.scan_complete:
    if st.session_state.celestial_bodies:
        st.success(f"Scan Complete! Found: {', '.join(st.session_state.celestial_bodies)}")

        # Create a selection box for the user to choose a planet
        selected_planet = st.selectbox(
            "Select a celestial body to learn more:",
            options=[""] + st.session_state.celestial_bodies, # Add an empty option
            format_func=lambda x: "Choose an option" if x == "" else x
        )

        if selected_planet:
            with st.spinner(f"Fetching details for {selected_planet}..."):
                try:
                    payload = {"planet_name": selected_planet}
                    response = requests.post(API_URL_DETAILS, json=payload, timeout=20)

                    if response.status_code == 200:
                        st.session_state.planet_details = response.json()
                    else:
                        st.error(f"API Error ({response.status_code}): {response.json().get('error')}")

                except requests.exceptions.ConnectionError:
                    st.error("Connection Error: Could not connect to the API server.")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")
    else:
        st.info("No celestial bodies were identified in the image.")

    # --- Display Planet Details ---
    if st.session_state.planet_details:
        details = st.session_state.planet_details
        if details.get('name') == selected_planet: # Ensure details match selection
            st.markdown("---")
            st.header(f"✨ Information about {details.get('name')}")
            st.write(details.get('summary'))

            st.subheader("Data for AR/VR Simulation")
            col1, col2, col3 = st.columns(3)
            col1.metric("Mass (kg)", value=details.get('mass_kg', 'N/A'))
            col2.metric("Mean Radius (km)", value=details.get('radius_km', 'N/A'))
            col3.metric("Axial Rotation", value=details.get('rotation_direction', 'N/A'))

# --- Button to Reset and Scan a New Image ---
if st.session_state.scan_complete:
    if st.button("Start Over"):
        reset_scan()
        st.rerun()